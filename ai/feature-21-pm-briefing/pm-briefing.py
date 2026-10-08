#!/usr/bin/env python3
"""Read dashboard + risks + changelog; post 5-sentence Slack briefing."""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import anthropic

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"


def read_latest_changelog_week(changelog_path: Path) -> str:
    """Extract the most recent weekly section from PROGRAM-CHANGELOG.md."""
    if not changelog_path.exists():
        return "No changelog available."
    text = changelog_path.read_text()
    # Find first ## Week of section
    match = re.search(r"(## Week of \d{4}-\d{2}-\d{2}.*?)(?=\n## Week of |\Z)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text[:2000]


def post_to_slack(webhook_url: str, message: str) -> None:
    resp = requests.post(webhook_url, json={"text": message})
    resp.raise_for_status()


def main() -> None:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY required.")
    if not slack_webhook:
        sys.exit("Error: SLACK_WEBHOOK_URL required.")

    dashboard_path = ROOT / "program" / "PROGRAM-DASHBOARD.md"
    risks_path = ROOT / "program" / "PROGRAM-RISKS.md"
    changelog_path = ROOT / "program" / "PROGRAM-CHANGELOG.md"

    dashboard_text = dashboard_path.read_text() if dashboard_path.exists() else "Dashboard not available."
    risks_text = risks_path.read_text() if risks_path.exists() else "No risks recorded."
    changelog_text = read_latest_changelog_week(changelog_path)

    client = anthropic.Anthropic(api_key=anthropic_key)
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    message = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": (
                    f"You are a program manager writing a Monday morning Slack briefing.\n\n"
                    f"Program Dashboard:\n{dashboard_text[:1500]}\n\n"
                    f"Program Risks:\n{risks_text[:1000]}\n\n"
                    f"This Week's Changelog:\n{changelog_text[:1000]}\n\n"
                    f"Write exactly 5 sentences suitable for posting in a Slack channel. "
                    f"Cover: overall program health, what shipped last week, current blockers, "
                    f"what needs PM attention, and one concrete action for this week. "
                    f"Be specific with initiative names and numbers. "
                    f"Output only the 5 sentences."
                ),
            }
        ],
    )

    briefing_text = message.content[0].text.strip()
    slack_message = f":bar_chart: *Program Hub — Weekly Briefing ({as_of})*\n\n{briefing_text}"

    print("Posting to Slack...")
    post_to_slack(slack_webhook, slack_message)
    print("Posted.")


if __name__ == "__main__":
    main()
