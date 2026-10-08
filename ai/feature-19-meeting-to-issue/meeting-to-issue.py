#!/usr/bin/env python3
"""CLI: read meeting notes; extract action items; create GitHub Issues in batch."""

import json
import os
import sys
from pathlib import Path

import yaml
import requests
import anthropic

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"


def gh_headers(token: str) -> dict:
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def extract_action_items(client: anthropic.Anthropic, notes: str, pods: list, initiatives: list) -> list:
    pod_labels = [p["label"] for p in pods]

    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Extract all action items from the following meeting notes as GitHub issues.\n\n"
                    f"Meeting notes:\n{notes}\n\n"
                    f"Available pod labels: {pod_labels}\n"
                    f"Available initiatives: {initiatives}\n\n"
                    f"Return a JSON array only (no markdown, no explanation):\n"
                    f'[{{"title": "...", "description": "...", "assignee": "..." or null, '
                    f'"initiative": "..." or null, "pod_label": "..." or null, '
                    f'"is_blocked": true/false, "is_dependency": true/false}}, ...]\n\n'
                    f"Extract every concrete action item, decision, or commitment mentioned. "
                    f"Use null for assignee/initiative/pod_label when not clear from context. "
                    f"is_blocked: true if the action is currently blocked on something. "
                    f"is_dependency: true if this action depends on another team or system."
                ),
            }
        ],
    )
    return json.loads(message.content[0].text.strip())


def create_issue(token: str, repo: str, title: str, body: str, labels: list, assignee: str | None) -> dict:
    payload = {"title": title, "body": body, "labels": labels}
    if assignee:
        payload["assignees"] = [assignee.lstrip("@")]
    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers=gh_headers(token),
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: meeting-to-issue.py <initiative-slug> [notes-file|-]")

    slug = sys.argv[1]
    notes_source = sys.argv[2] if len(sys.argv) > 2 else "-"

    if notes_source == "-":
        notes = sys.stdin.read()
    else:
        notes = Path(notes_source).read_text()

    if not notes.strip():
        sys.exit("Error: no meeting notes provided.")

    gh_token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not gh_token:
        sys.exit("Error: OCTO_PAT or GITHUB_TOKEN required.")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY required.")

    config_path = ROOT / "initiatives" / slug / "config.yml"
    if not config_path.exists():
        sys.exit(f"Error: initiative '{slug}' not found.")
    config = yaml.safe_load(config_path.read_text())
    repo = config["source_repo"]
    pods = config.get("pods", [])
    blocked_label = config["labels"]["blocked"]
    dep_label = config["labels"]["dependency"]

    # Collect all initiative names for context
    initiatives = []
    for cp in sorted((ROOT / "initiatives").glob("*/config.yml")):
        cfg = yaml.safe_load(cp.read_text())
        initiatives.append(cfg["name"])

    client = anthropic.Anthropic(api_key=anthropic_key)

    print("Extracting action items from meeting notes...")
    action_items = extract_action_items(client, notes, pods, initiatives)
    print(f"Extracted {len(action_items)} action items.")

    for item in action_items:
        title = item.get("title", "Untitled action item")
        description = item.get("description", "")
        assignee = item.get("assignee")
        pod_label = item.get("pod_label")

        labels = []
        if pod_label and pod_label in [p["label"] for p in pods]:
            labels.append(pod_label)
        if item.get("is_blocked"):
            labels.append(blocked_label)
        if item.get("is_dependency"):
            labels.append(dep_label)

        print(f"Creating: {title[:70]}...")
        issue = create_issue(gh_token, repo, title, description, labels, assignee)
        print(f"  #{issue['number']}: {issue['html_url']}")

    print(f"\nCreated {len(action_items)} issues in {repo}.")


if __name__ == "__main__":
    main()
