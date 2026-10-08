#!/usr/bin/env python3
"""Every Monday: scan source repos for issues open >14 days with zero comments; post nudge."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
import requests
import anthropic

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"


def gh_headers(token: str) -> dict:
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def gh_search(token: str, query: str) -> list:
    items = []
    page = 1
    while True:
        resp = requests.get(
            "https://api.github.com/search/issues",
            headers=gh_headers(token),
            params={"q": query, "per_page": 100, "page": page},
        )
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("items", []))
        if len(items) >= data.get("total_count", 0) or not data.get("items"):
            break
        page += 1
    return items


def post_comment(token: str, repo: str, issue_number: int, body: str) -> None:
    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        headers=gh_headers(token),
        json={"body": body},
    )
    resp.raise_for_status()


def generate_nudge(client: anthropic.Anthropic, issue_title: str, issue_body: str, days_open: int) -> str:
    body_snippet = (issue_body or "")[:500]
    message = client.messages.create(
        model=MODEL,
        max_tokens=150,
        messages=[
            {
                "role": "user",
                "content": (
                    f"This GitHub issue has been open for {days_open} days with no comments:\n\n"
                    f"Title: {issue_title}\n\n"
                    f"Description: {body_snippet}\n\n"
                    f"Write a single friendly sentence to nudge the assignee to update the issue "
                    f"or ask for help if needed. Be specific to the issue content. "
                    f"Do not start with 'I' or use the word 'nudge'. Output only the sentence."
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
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for config_path in sorted(initiatives_dir.glob("*/config.yml")):
        cfg = yaml.safe_load(config_path.read_text())
        repo = cfg["source_repo"]
        print(f"Scanning {repo} for stale issues...")

        stale_issues = gh_search(
            gh_token,
            f"repo:{repo} is:issue is:open comments:0 created:<={stale_cutoff[:10]}"
        )

        print(f"  Found {len(stale_issues)} stale issues.")

        for issue in stale_issues:
            days_open = (datetime.now(timezone.utc) - datetime.fromisoformat(
                issue["created_at"].replace("Z", "+00:00")
            )).days
            print(f"  Generating nudge for #{issue['number']}: {issue['title'][:60]}...")
            nudge = generate_nudge(client, issue["title"], issue.get("body", ""), days_open)
            comment = (
                f":alarm_clock: **Stale issue check-in** — this issue has been open for "
                f"{days_open} days with no comments.\n\n{nudge}\n\n"
                f"*This comment was generated automatically by Program Hub.*"
            )
            post_comment(gh_token, repo, issue["number"], comment)
            print(f"    Posted nudge comment.")

    print("Stale issue coach complete.")


if __name__ == "__main__":
    main()
