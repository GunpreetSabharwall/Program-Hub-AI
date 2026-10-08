#!/usr/bin/env python3
"""Estimate showcase on-track confidence per initiative; add column to dashboard."""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
import requests
import anthropic

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"


def gh_headers(token: str) -> dict:
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def gh_search_count(token: str, query: str) -> int:
    resp = requests.get(
        "https://api.github.com/search/issues",
        headers=gh_headers(token),
        params={"q": query, "per_page": 1},
    )
    resp.raise_for_status()
    return resp.json().get("total_count", 0)


def read_closure_rate(slug: str) -> float:
    """Read closed issues last 7 days from STATUS.md."""
    status_path = ROOT / "initiatives" / slug / "STATUS.md"
    if not status_path.exists():
        return 0.0
    text = status_path.read_text()
    match = re.search(r"\| Issues closed \(last 7 days\) \| (\d+) \|", text)
    return float(match.group(1)) if match else 0.0


def weeks_remaining(showcase_date_str: str) -> float:
    showcase = datetime.fromisoformat(str(showcase_date_str)).date()
    today = datetime.now(timezone.utc).date()
    days = (showcase - today).days
    return max(0.0, days / 7.0)


def confidence_pct(closure_rate: float, weeks_rem: float, open_issues: int) -> float:
    if open_issues == 0:
        return 100.0
    if closure_rate == 0 or weeks_rem == 0:
        return 0.0
    return min(100.0, (closure_rate * weeks_rem / open_issues) * 100.0)


def explain_confidence(client: anthropic.Anthropic, initiative_name: str, confidence: float,
                       open_issues: int, closure_rate: float, weeks_rem: float) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{initiative_name}: {open_issues} open issues, "
                    f"closing {closure_rate:.1f}/week, {weeks_rem:.1f} weeks to showcase, "
                    f"confidence score {confidence:.0f}%. "
                    f"Write one sentence explaining this forecast for a program manager. "
                    f"Output only the sentence."
                ),
            }
        ],
    )
    return message.content[0].text.strip()


def main() -> None:
    gh_token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not gh_token:
        sys.exit("Error: OCTO_PAT or GITHUB_TOKEN required.")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY required.")

    client = anthropic.Anthropic(api_key=anthropic_key)
    initiatives_dir = ROOT / "initiatives"
    forecast_rows = []

    for config_path in sorted(initiatives_dir.glob("*/config.yml")):
        cfg = yaml.safe_load(config_path.read_text())
        slug = cfg["slug"]
        repo = cfg["source_repo"]
        showcase_date = cfg.get("showcase_date", "")

        if not showcase_date:
            continue

        print(f"Forecasting {cfg['name']}...")
        open_issues = gh_search_count(gh_token, f"repo:{repo} is:issue is:open")
        closure_rate = read_closure_rate(slug)
        weeks_rem = weeks_remaining(str(showcase_date))
        conf = confidence_pct(closure_rate, weeks_rem, open_issues)

        explanation = explain_confidence(client, cfg["name"], conf, open_issues, closure_rate, weeks_rem)

        forecast_rows.append({
            "name": cfg["name"],
            "confidence": f"{conf:.0f}%",
            "explanation": explanation,
        })

    # Update PROGRAM-DASHBOARD.md
    dash_path = ROOT / "program" / "PROGRAM-DASHBOARD.md"
    if not dash_path.exists():
        print("PROGRAM-DASHBOARD.md not found — skipping.")
        return

    text = dash_path.read_text()
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    section_lines = [
        "",
        "## Showcase Confidence",
        "",
        f"*Generated {as_of} — Formula: min(100, closure_rate × weeks_remaining / open_issues × 100)*",
        "",
        "| Initiative | Confidence | Assessment |",
        "|------------|------------|------------|",
    ]
    for row in forecast_rows:
        section_lines.append(f"| {row['name']} | {row['confidence']} | {row['explanation']} |")

    section = "\n".join(section_lines)

    marker = "## Showcase Confidence"
    if marker in text:
        start = text.index(marker)
        next_section = text.find("\n## ", start + 5)
        if next_section != -1:
            text = text[:start] + section[1:] + "\n" + text[next_section:]
        else:
            text = text[:start] + section[1:] + "\n"
    else:
        text = text.rstrip() + "\n" + section + "\n"

    dash_path.write_text(text)
    print(f"Updated {dash_path}")


if __name__ == "__main__":
    main()
