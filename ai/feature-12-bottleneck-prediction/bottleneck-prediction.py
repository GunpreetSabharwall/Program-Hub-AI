#!/usr/bin/env python3
"""Predict issues likely to block in next 7 days; add to PROGRAM-RISKS.md. Uses prompt caching."""

import json
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

SYSTEM_PROMPT = """You are a program manager with deep engineering experience.
Your task is to predict which open issues are most likely to become blockers in the next 7 days,
based on issue metadata and historical patterns.

Signals that predict future blockers:
- Issue age > 10 days with no comments (stale)
- Issue assigned to a person who has other blocked issues
- Issue title mentions API contract, external dependency, or cross-team work
- Issue has been re-opened or has many comments (contested)
- Issue is near the end of a sprint and has low comment activity
- Similar issues in closed history that became blocked

For each initiative, return a JSON array of at-risk issues (maximum 5):
[{"issue_number": N, "title": "...", "reason": "one sentence explaining why this is at risk",
  "confidence": "high|medium|low"}, ...]

Return JSON only — no markdown, no explanation. Return [] if no issues are at risk."""


def gh_headers(token: str) -> dict:
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def gh_get_issues(token: str, repo: str, state: str = "open", limit: int = 100) -> list:
    items = []
    page = 1
    while len(items) < limit:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            headers=gh_headers(token),
            params={"state": state, "per_page": min(100, limit - len(items)), "page": page},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        items.extend([i for i in data if "pull_request" not in i])
        if len(data) < 100:
            break
        page += 1
    return items[:limit]


def read_velocity(slug: str) -> float:
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


def summarise_issues(issues: list) -> str:
    lines = []
    for issue in issues[:60]:
        labels = [l["name"] for l in issue.get("labels", [])]
        assignee = issue["assignee"]["login"] if issue.get("assignee") else "unassigned"
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(
            issue["created_at"].replace("Z", "+00:00")
        )).days
        comments = issue.get("comments", 0)
        lines.append(
            f"#{issue['number']}: {issue['title']} "
            f"[age={age}d, comments={comments}, assignee={assignee}, labels={','.join(labels) or 'none'}]"
        )
    return "\n".join(lines)


def main() -> None:
    gh_token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not gh_token:
        sys.exit("Error: OCTO_PAT or GITHUB_TOKEN required.")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY required.")

    client = anthropic.Anthropic(api_key=anthropic_key)
    initiatives_dir = ROOT / "initiatives"

    all_predictions = []

    for config_path in sorted(initiatives_dir.glob("*/config.yml")):
        cfg = yaml.safe_load(config_path.read_text())
        slug = cfg["slug"]
        name = cfg["name"]
        repo = cfg["source_repo"]
        showcase_date = cfg.get("showcase_date", "")

        print(f"Predicting bottlenecks for {name}...")
        open_issues = gh_get_issues(gh_token, repo, state="open")
        closed_blocked = gh_get_issues(gh_token, repo, state="closed", limit=30)
        velocity = read_velocity(slug)
        weeks_rem = weeks_remaining(str(showcase_date)) if showcase_date else 0.0

        open_summary = summarise_issues(open_issues)
        closed_summary = summarise_issues(closed_blocked)

        user_content = (
            f"Initiative: {name}\n"
            f"Velocity: {velocity:.0f} issues closed last week\n"
            f"Weeks to showcase: {weeks_rem:.1f}\n\n"
            f"Open issues:\n{open_summary}\n\n"
            f"Recently closed issues (for pattern reference):\n{closed_summary}\n\n"
            f"Which open issues are most likely to become blockers in the next 7 days?"
        )

        message = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        try:
            predictions = json.loads(message.content[0].text.strip())
            for p in predictions:
                p["initiative"] = name
                p["repo"] = repo
            all_predictions.extend(predictions)
        except json.JSONDecodeError:
            print(f"  Warning: could not parse JSON response for {name}")

    # Add "Predicted Risks — Next 7 Days" section to PROGRAM-RISKS.md
    risks_path = ROOT / "program" / "PROGRAM-RISKS.md"
    if not risks_path.exists():
        print("PROGRAM-RISKS.md not found — skipping.")
        return

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    text = risks_path.read_text()

    section_lines = [
        f"## Predicted Risks — Next 7 Days",
        "",
        f"*AI-generated {as_of} — review with engineering leads before escalating*",
        "",
        "| Initiative | Issue | Confidence | Prediction |",
        "|------------|-------|------------|------------|",
    ]

    confidence_order = {"high": 0, "medium": 1, "low": 2}
    all_predictions.sort(key=lambda p: confidence_order.get(p.get("confidence", "low"), 2))

    if all_predictions:
        for p in all_predictions:
            issue_ref = f"{p['repo']}#{p['issue_number']}"
            title = p.get("title", "").replace("|", "\\|")
            reason = p.get("reason", "").replace("|", "\\|")
            conf = p.get("confidence", "medium").capitalize()
            section_lines.append(f"| {p['initiative']} | {issue_ref} {title} | {conf} | {reason} |")
    else:
        section_lines.append("| — | No predicted risks | — | — |")

    section_lines += ["", "---", ""]
    section = "\n".join(section_lines)

    marker = "## Predicted Risks"
    if marker in text:
        start = text.index(marker)
        next_section = text.find("\n## ", start + 5)
        table_marker = "## Cross-Initiative Risk Table"
        if table_marker in text and table_marker in text[start:]:
            idx = text.index(table_marker, start)
            text = text[:start] + section + text[idx:]
        elif next_section != -1:
            text = text[:start] + section + text[next_section + 1:]
        else:
            text = text[:start] + section
    else:
        # Insert before the cross-initiative table
        table_marker = "## Cross-Initiative Risk Table"
        if table_marker in text:
            idx = text.index(table_marker)
            text = text[:idx] + section + text[idx:]
        else:
            text = section + text

    risks_path.write_text(text)
    print(f"Updated {risks_path}")


if __name__ == "__main__":
    main()
