#!/usr/bin/env python3
"""Read dashboard + risks + changelog + AEV value; post 5-sentence Slack briefing.

    python ai/feature-21-pm-briefing/pm-briefing.py            # post to Slack
    python ai/feature-21-pm-briefing/pm-briefing.py --print    # print instead (no Slack needed)
    python ai/feature-21-pm-briefing/pm-briefing.py --print --no-ai   # fixed template, no API call
    ... --aev-json SLUG=PATH    # read an initiative's AEV results from a local file
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"

sys.path.insert(0, str(ROOT / "scripts"))
import aev_value  # noqa: E402


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


def value_section(overrides: dict) -> tuple:
    """(facts text for the prompt, attention items) from every AEV-enabled initiative."""
    token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    facts, attention = [], []
    for entry in aev_value.load_all(overrides, token):
        cfg, results = entry["cfg"], entry["results"]
        if results is None:
            facts.append(f"{cfg['name']}: AEV is not set up yet.")
            continue
        facts.append(aev_value.briefing_facts(cfg, results))
        attention += aev_value.attention_items(cfg, results)
    return "\n\n".join(facts) or "No initiative reports AEV value yet.", attention


def template_briefing(value_attention: list) -> str:
    """Fallback when there is no API key or the API call fails: no AI, just the facts."""
    clean = [a.replace("**", "") for a in value_attention]
    if not clean:
        return "No value signals need attention this week. See PROGRAM-DASHBOARD.md for delivery health."
    return " ".join(clean[:5])


def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly PM briefing.")
    parser.add_argument("--print", dest="print_only", action="store_true",
                        help="Print the briefing instead of posting it to Slack.")
    parser.add_argument("--no-ai", action="store_true", help="Use the fixed template; no API call.")
    parser.add_argument("--aev-json", action="append", metavar="SLUG=PATH",
                        help="Read this initiative's AEV results from a local file (repeatable).")
    args = parser.parse_args()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not anthropic_key and not args.no_ai:
        sys.exit("Error: ANTHROPIC_API_KEY required (or use --no-ai).")
    if not slack_webhook and not args.print_only:
        sys.exit("Error: SLACK_WEBHOOK_URL required (or use --print).")

    dashboard_path = ROOT / "program" / "PROGRAM-DASHBOARD.md"
    risks_path = ROOT / "program" / "PROGRAM-RISKS.md"
    changelog_path = ROOT / "program" / "PROGRAM-CHANGELOG.md"

    dashboard_text = dashboard_path.read_text() if dashboard_path.exists() else "Dashboard not available."
    risks_text = risks_path.read_text() if risks_path.exists() else "No risks recorded."
    changelog_text = read_latest_changelog_week(changelog_path)
    value_text, value_attention = value_section(aev_value.parse_overrides(args.aev_json))

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    briefing_text = None
    if not args.no_ai:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model=MODEL,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"You are a program manager writing a Monday morning Slack briefing.\n\n"
                            f"Program Dashboard:\n{dashboard_text[:2500]}\n\n"
                            f"Value (Agentic Earned Value, exact figures):\n{value_text[:2000]}\n\n"
                            f"Program Risks:\n{risks_text[:1000]}\n\n"
                            f"This Week's Changelog:\n{changelog_text[:1000]}\n\n"
                            f"Write exactly 5 sentences suitable for posting in a Slack channel. "
                            f"Cover: overall program health (delivery and value, and say so plainly "
                            f"if they disagree), what shipped last week, where AI-assisted work is and "
                            f"is not paying back its cost, what needs PM attention, and one concrete "
                            f"action for this week. Use the exact figures given; do not invent numbers. "
                            f"Be specific with initiative and pod names. "
                            f"Output only the 5 sentences."
                        ),
                    }
                ],
            )
            briefing_text = message.content[0].text.strip()
        except Exception as exc:  # fail loud, but still produce a briefing
            print(f"AI briefing failed ({exc}); using the fixed template.", file=sys.stderr)
    if briefing_text is None:
        briefing_text = template_briefing(value_attention)

    slack_message = f":bar_chart: *Program Hub — Weekly Briefing ({as_of})*\n\n{briefing_text}"

    if args.print_only:
        print(slack_message)
        return

    print("Posting to Slack...")
    post_to_slack(slack_webhook, slack_message)
    print("Posted.")


if __name__ == "__main__":
    main()
