#!/usr/bin/env python3
"""Add all open issues to project board; set fields from config."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
import requests

ROOT = Path(__file__).parent.parent


def gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }


def graphql(token: str, query: str, variables: dict) -> dict:
    resp = requests.post(
        "https://api.github.com/graphql",
        headers=gh_headers(token),
        json={"query": query, "variables": variables},
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def rest_get(token: str, url: str, params: dict = None) -> dict:
    resp = requests.get(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }, params=params or {})
    resp.raise_for_status()
    return resp.json()


def get_open_issues(token: str, repo: str) -> list:
    owner, repo_name = repo.split("/", 1)
    items = []
    page = 1
    while True:
        data = rest_get(
            token,
            f"https://api.github.com/repos/{repo}/issues",
            {"state": "open", "per_page": 100, "page": page},
        )
        if not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
    return [i for i in items if "pull_request" not in i]


def get_project_items(token: str, project_id: str) -> set:
    """Return set of issue node IDs already in the project."""
    data = graphql(
        token,
        """
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: 100) {
                nodes {
                  content {
                    ... on Issue { id }
                  }
                }
              }
            }
          }
        }
        """,
        {"projectId": project_id},
    )
    existing = set()
    for node in data["node"]["items"]["nodes"]:
        content = node.get("content") or {}
        if content.get("id"):
            existing.add(content["id"])
    return existing


def get_issue_node_id(token: str, owner: str, repo_name: str, issue_number: int) -> str:
    data = graphql(
        token,
        """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) { id }
          }
        }
        """,
        {"owner": owner, "repo": repo_name, "number": issue_number},
    )
    return data["repository"]["issue"]["id"]


def add_item(token: str, project_id: str, node_id: str) -> str:
    data = graphql(
        token,
        """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item { id }
          }
        }
        """,
        {"projectId": project_id, "contentId": node_id},
    )
    return data["addProjectV2ItemById"]["item"]["id"]


def get_project_fields(token: str, project_id: str) -> dict:
    data = graphql(
        token,
        """
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 20) {
                nodes {
                  ... on ProjectV2SingleSelectField { id name options { id name } }
                  ... on ProjectV2Field { id name dataType }
                  ... on ProjectV2IterationField { id name }
                }
              }
            }
          }
        }
        """,
        {"projectId": project_id},
    )
    fields = {}
    for node in data["node"]["fields"]["nodes"]:
        if node.get("name"):
            options = {opt["name"]: opt["id"] for opt in node.get("options", [])}
            fields[node["name"]] = {"id": node["id"], "options": options, "dataType": node.get("dataType", "")}
    return fields


def set_text_field(token: str, project_id: str, item_id: str, field_id: str, value: str) -> None:
    graphql(
        token,
        """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId itemId: $itemId fieldId: $fieldId
            value: { text: $value }
          }) { projectV2Item { id } }
        }
        """,
        {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "value": value},
    )


def set_date_field(token: str, project_id: str, item_id: str, field_id: str, value: str) -> None:
    graphql(
        token,
        """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: Date!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId itemId: $itemId fieldId: $fieldId
            value: { date: $value }
          }) { projectV2Item { id } }
        }
        """,
        {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "value": value},
    )


def set_select_field(token: str, project_id: str, item_id: str, field_id: str, option_id: str) -> None:
    graphql(
        token,
        """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId itemId: $itemId fieldId: $fieldId
            value: { singleSelectOptionId: $optionId }
          }) { projectV2Item { id } }
        }
        """,
        {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "optionId": option_id},
    )


def get_pod_for_issue(issue: dict, pods: list) -> str | None:
    issue_labels = {lbl["name"] for lbl in issue.get("labels", [])}
    for pod in pods:
        if pod["label"] in issue_labels:
            return pod["name"]
    return None


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: sync-project-board.py <initiative-slug>")

    slug = sys.argv[1]
    token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Error: OCTO_PAT or GITHUB_TOKEN env var required.")

    config_path = ROOT / "initiatives" / slug / "config.yml"
    config = yaml.safe_load(config_path.read_text())
    repo = config["source_repo"]
    project_id = config.get("github_project_id", "")

    if not project_id:
        print(f"No github_project_id configured for {slug} — skipping.")
        return

    owner, repo_name = repo.split("/", 1)
    start_date = str(config.get("week_start", ""))
    end_date = str(config.get("showcase_date", ""))
    initiative_name = config["name"]
    pods = config.get("pods", [])

    print(f"Fetching open issues for {repo}...")
    issues = get_open_issues(token, repo)
    print(f"Found {len(issues)} open issues.")

    print("Fetching existing project board items...")
    existing_node_ids = get_project_items(token, project_id)

    print("Fetching project fields...")
    fields = get_project_fields(token, project_id)

    for issue in issues:
        print(f"  Processing #{issue['number']}: {issue['title'][:60]}")
        node_id = get_issue_node_id(token, owner, repo_name, issue["number"])

        if node_id not in existing_node_ids:
            item_id = add_item(token, project_id, node_id)
            print(f"    Added to project as item {item_id}")
        else:
            # We don't have the item_id for existing items without another query; skip field updates for them
            print(f"    Already in project — skipping field updates")
            continue

        # Set Initiative field
        if "Initiative" in fields:
            f = fields["Initiative"]
            if f.get("dataType") == "TEXT" or not f["options"]:
                set_text_field(token, project_id, item_id, f["id"], initiative_name)
            else:
                opt_id = f["options"].get(initiative_name)
                if opt_id:
                    set_select_field(token, project_id, item_id, f["id"], opt_id)

        # Set Pod field
        pod_name = get_pod_for_issue(issue, pods)
        if pod_name and "Pod" in fields:
            f = fields["Pod"]
            if f.get("dataType") == "TEXT" or not f["options"]:
                set_text_field(token, project_id, item_id, f["id"], pod_name)
            else:
                opt_id = f["options"].get(pod_name)
                if opt_id:
                    set_select_field(token, project_id, item_id, f["id"], opt_id)

        # Set Start Date
        if start_date and "Start Date" in fields:
            try:
                set_date_field(token, project_id, item_id, fields["Start Date"]["id"], start_date)
            except Exception as e:
                print(f"    Warning: could not set Start Date: {e}")

        # Set End Date
        if end_date and "End Date" in fields:
            try:
                set_date_field(token, project_id, item_id, fields["End Date"]["id"], end_date)
            except Exception as e:
                print(f"    Warning: could not set End Date: {e}")

    print("Sync complete.")


if __name__ == "__main__":
    main()
