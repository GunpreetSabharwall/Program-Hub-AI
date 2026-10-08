#!/usr/bin/env python3
"""CLI: free text → structured GitHub Issue."""

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


def parse_issue(client: anthropic.Anthropic, text: str, pods: list) -> dict:
    pod_labels = [p["label"] for p in pods]
    pod_names = [p["name"] for p in pods]

    message = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Parse the following note into a structured GitHub issue.\n\n"
                    f"Note: {text}\n\n"
                    f"Available pod labels: {pod_labels}\n"
                    f"Pod names: {pod_names}\n\n"
                    f"Return JSON only (no markdown, no explanation):\n"
                    f'{{"title": "...", "description": "...", "pod_label": "..." or null, '
                    f'"is_blocked": true/false, "is_dependency": true/false}}\n\n'
                    f"title: clear, concise issue title (max 80 chars)\n"
                    f"description: 1-3 sentences of context as GitHub issue body\n"
                    f"pod_label: the most appropriate pod label from the list, or null\n"
                    f"is_blocked: true if the note indicates this work is currently blocked\n"
                    f"is_dependency: true if this represents a dependency on another team/system"
                ),
            }
        ],
    )
    return json.loads(message.content[0].text.strip())


def create_issue(token: str, repo: str, title: str, body: str, labels: list) -> dict:
    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers=gh_headers(token),
        json={"title": title, "body": body, "labels": labels},
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Usage: nl-issue-creation.py <initiative-slug> \"<free text>\"")

    slug = sys.argv[1]
    text = " ".join(sys.argv[2:])

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

    client = anthropic.Anthropic(api_key=anthropic_key)

    print("Parsing issue from text...")
    parsed = parse_issue(client, text, pods)
    print(f"Parsed: {json.dumps(parsed, indent=2)}")

    labels = []
    if parsed.get("pod_label"):
        labels.append(parsed["pod_label"])
    if parsed.get("is_blocked"):
        labels.append(config["labels"]["blocked"])
    if parsed.get("is_dependency"):
        labels.append(config["labels"]["dependency"])

    print(f"Creating issue in {repo}...")
    issue = create_issue(gh_token, repo, parsed["title"], parsed.get("description", ""), labels)
    print(f"Created issue #{issue['number']}: {issue['html_url']}")


if __name__ == "__main__":
    main()
