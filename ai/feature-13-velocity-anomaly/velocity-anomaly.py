#!/usr/bin/env python3
"""Compute 4-week rolling velocity per pod; flag anomalies; explain with Claude."""

import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml
import anthropic

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"


def get_historical_closed_counts(slug: str, pod_slug: str, weeks: int = 4) -> list[int]:
    """Read STATUS.md from git history to extract closed issue counts per week."""
    status_file = f"initiatives/{slug}/STATUS.md"
    counts = []

    result = subprocess.run(
        ["git", "log", "--format=%H", "--", status_file],
        cwd=ROOT, capture_output=True, text=True,
    )
    commits = result.stdout.strip().splitlines()

    for commit in commits[:weeks]:
        result = subprocess.run(
            ["git", "show", f"{commit}:{status_file}"],
            cwd=ROOT, capture_output=True, text=True,
        )
        text = result.stdout
        # Extract closed count from table
        match = re.search(r"\| Issues closed \(last 7 days\) \| (\d+) \|", text)
        if match:
            counts.append(int(match.group(1)))

    # Pad with zeros if fewer than requested weeks available
    while len(counts) < weeks:
        counts.append(0)

    return counts[:weeks]


def classify_anomaly(current: int, baseline: float) -> str:
    if baseline == 0:
        return "Red" if current == 0 else "Green"
    pct_below = (baseline - current) / baseline
    if pct_below > 0.5 or current == 0:
        return "Red"
    elif pct_below > 0.3:
        return "Amber"
    else:
        return "Green"


def explain_anomaly(client: anthropic.Anthropic, initiative_name: str, pod_name: str,
                    current: int, baseline: float, history: list) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Program management context: {pod_name} in {initiative_name} closed "
                    f"{current} issues this week. Their 4-week average is {baseline:.1f} issues/week. "
                    f"Weekly history (oldest first): {history}.\n\n"
                    f"Write one sentence explaining the most likely cause of this velocity change. "
                    f"Be concrete. Output only the sentence."
                ),
            }
        ],
    )
    return message.content[0].text.strip()


def emoji(signal: str) -> str:
    return {"Green": "🟢", "Amber": "🟡", "Red": "🔴"}.get(signal, "⚪")


def main() -> None:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY required.")

    client = anthropic.Anthropic(api_key=anthropic_key)

    initiatives_dir = ROOT / "initiatives"
    velocity_rows = []

    for config_path in sorted(initiatives_dir.glob("*/config.yml")):
        cfg = yaml.safe_load(config_path.read_text())
        slug = cfg["slug"]
        initiative_name = cfg["name"]

        for pod in cfg.get("pods", []):
            pod_name = pod["name"]
            pod_slug = pod["slug"]

            history = get_historical_closed_counts(slug, pod_slug)
            current = history[0] if history else 0
            baseline = sum(history[1:]) / max(len(history[1:]), 1) if len(history) > 1 else float(current)

            signal = classify_anomaly(current, baseline)

            explanation = ""
            if signal in ("Amber", "Red"):
                print(f"Explaining anomaly for {pod_name} ({signal})...")
                explanation = explain_anomaly(client, initiative_name, pod_name, current, baseline, history)

            velocity_rows.append({
                "initiative": initiative_name,
                "pod": pod_name,
                "current": current,
                "baseline": f"{baseline:.1f}",
                "signal": signal,
                "explanation": explanation,
            })

    # Update PROGRAM-DASHBOARD.md with Velocity Signal section
    dash_path = ROOT / "program" / "PROGRAM-DASHBOARD.md"
    if not dash_path.exists():
        print("PROGRAM-DASHBOARD.md not found — skipping.")
        return

    text = dash_path.read_text()
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    velocity_section_lines = [
        "",
        "## Velocity Signal",
        "",
        f"*Generated {as_of} — Green: within 30% of baseline, Amber: 30-50% below, Red: >50% below or zero*",
        "",
        "| Initiative | Pod | This Week | 4-Week Avg | Signal | Note |",
        "|------------|-----|-----------|------------|--------|------|",
    ]
    for row in velocity_rows:
        note = row["explanation"] or "—"
        velocity_section_lines.append(
            f"| {row['initiative']} | {row['pod']} | {row['current']} | "
            f"{row['baseline']} | {emoji(row['signal'])} {row['signal']} | {note} |"
        )

    velocity_section = "\n".join(velocity_section_lines)

    marker = "## Velocity Signal"
    if marker in text:
        # Replace existing section
        start = text.index(marker)
        # Find next ## heading or end of file
        next_section = text.find("\n## ", start + 5)
        if next_section != -1:
            text = text[:start] + velocity_section[1:] + "\n" + text[next_section:]
        else:
            text = text[:start] + velocity_section[1:] + "\n"
    else:
        text = text.rstrip() + "\n" + velocity_section + "\n"

    dash_path.write_text(text)
    print(f"Updated {dash_path}")


if __name__ == "__main__":
    main()
