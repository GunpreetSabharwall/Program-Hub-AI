#!/usr/bin/env python3
"""Set Risk Level field on GitHub Project board item via GraphQL."""

import os
import sys
import json
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


def find_project_id_for_repo(configs_dir: Path, repo: str) -> str | None:
    """Find github_project_id from initiative configs matching the source repo."""
    for config_path in configs_dir.glob("*/config.yml"):
        cfg = yaml.safe_load(config_path.read_text())
        if cfg.get("source_repo") == repo and cfg.get("github_project_id"):
            return cfg["github_project_id"]
    return None


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


def get_project_fields(token: str, project_id: str) -> dict:
    """Return {field_name: {id, options: {option_name: option_id}}}."""
    data = graphql(
        token,
        """
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 20) {
                nodes {
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    options { id name }
                  }
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
            fields[node["name"]] = {"id": node["id"], "options": options}
    return fields


def add_item_to_project(token: str, project_id: str, issue_node_id: str) -> str:
    data = graphql(
        token,
        """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item { id }
          }
        }
        """,
        {"projectId": project_id, "contentId": issue_node_id},
    )
    return data["addProjectV2ItemById"]["item"]["id"]


def set_field_value(token: str, project_id: str, item_id: str, field_id: str, option_id: str) -> None:
    graphql(
        token,
        """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { singleSelectOptionId: $optionId }
          }) {
            projectV2Item { id }
          }
        }
        """,
        {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "optionId": option_id},
    )


def main() -> None:
    if len(sys.argv) < 4:
        sys.exit("Usage: flag-project-risk.py <owner/repo> <issue-number> <label>")

    repo_full = sys.argv[1]
    issue_number = int(sys.argv[2])
    label = sys.argv[3]

    token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Error: OCTO_PAT or GITHUB_TOKEN env var required.")

    owner, repo_name = repo_full.split("/", 1)

    project_id = find_project_id_for_repo(ROOT / "initiatives", repo_full)
    if not project_id:
        print(f"No github_project_id configured for {repo_full} — skipping project board update.")
        return

    risk_level = "High" if label == "blocked" else "Medium"

    print(f"Getting issue node ID for {repo_full}#{issue_number}...")
    issue_node_id = get_issue_node_id(token, owner, repo_name, issue_number)

    print(f"Adding issue to project {project_id}...")
    item_id = add_item_to_project(token, project_id, issue_node_id)

    print(f"Fetching project fields...")
    fields = get_project_fields(token, project_id)

    risk_field = fields.get("Risk Level")
    if not risk_field:
        print("Warning: 'Risk Level' field not found on project board — skipping.")
        return

    option_id = risk_field["options"].get(risk_level)
    if not option_id:
        print(f"Warning: option '{risk_level}' not found in Risk Level field — skipping.")
        return

    print(f"Setting Risk Level = {risk_level} on item {item_id}...")
    set_field_value(token, project_id, item_id, risk_field["id"], option_id)
    print("Done.")


if __name__ == "__main__":
    main()
