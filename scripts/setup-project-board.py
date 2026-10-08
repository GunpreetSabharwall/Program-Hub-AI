#!/usr/bin/env python3
"""Create GitHub Project V2 with 8 custom fields."""

import os
import sys
import requests

ROOT_FIELDS = [
    # (name, field_type, options_or_datatype)
    ("Pod", "SINGLE_SELECT", ["Pod 1", "Pod 2", "Pod 3"]),
    ("Initiative", "SINGLE_SELECT", ["Example Initiative"]),
    ("Risk Level", "SINGLE_SELECT", ["High", "Medium", "Low"]),
    ("Sprint", "TEXT", None),
    ("Start Date", "DATE", None),
    ("End Date", "DATE", None),
    ("Showcase Ready", "SINGLE_SELECT", ["Yes", "No", "In Progress"]),
    ("Dependency On", "TEXT", None),
]


def graphql(token: str, query: str, variables: dict) -> dict:
    resp = requests.post(
        "https://api.github.com/graphql",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables},
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def get_owner_id(token: str, login: str) -> str:
    data = graphql(
        token,
        """
        query($login: String!) {
          user(login: $login) { id }
          organization(login: $login) { id }
        }
        """,
        {"login": login},
    )
    if data.get("organization") and data["organization"]:
        return data["organization"]["id"]
    if data.get("user") and data["user"]:
        return data["user"]["id"]
    raise RuntimeError(f"Could not find owner ID for '{login}'")


def create_project(token: str, owner_id: str, title: str) -> str:
    data = graphql(
        token,
        """
        mutation($ownerId: ID!, $title: String!) {
          createProjectV2(input: {ownerId: $ownerId, title: $title}) {
            projectV2 { id }
          }
        }
        """,
        {"ownerId": owner_id, "title": title},
    )
    return data["createProjectV2"]["projectV2"]["id"]


def create_single_select_field(token: str, project_id: str, name: str, options: list) -> str:
    opt_inputs = [{"name": o, "color": "GRAY", "description": ""} for o in options]
    data = graphql(
        token,
        """
        mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
          createProjectV2Field(input: {
            projectId: $projectId
            dataType: SINGLE_SELECT
            name: $name
            singleSelectOptions: $options
          }) {
            projectV2Field {
              ... on ProjectV2SingleSelectField { id }
            }
          }
        }
        """,
        {"projectId": project_id, "name": name, "options": opt_inputs},
    )
    return data["createProjectV2Field"]["projectV2Field"]["id"]


def create_field(token: str, project_id: str, name: str, data_type: str) -> str:
    data = graphql(
        token,
        """
        mutation($projectId: ID!, $name: String!, $dataType: ProjectV2CustomFieldType!) {
          createProjectV2Field(input: {
            projectId: $projectId
            dataType: $dataType
            name: $name
          }) {
            projectV2Field {
              ... on ProjectV2Field { id }
            }
          }
        }
        """,
        {"projectId": project_id, "name": name, "dataType": data_type},
    )
    return data["createProjectV2Field"]["projectV2Field"]["id"]


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Usage: setup-project-board.py <owner-login> <project-title>")

    owner_login = sys.argv[1]
    project_title = sys.argv[2]

    token = os.environ.get("OCTO_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Error: OCTO_PAT or GITHUB_TOKEN env var required.")

    print(f"Getting owner ID for '{owner_login}'...")
    owner_id = get_owner_id(token, owner_login)

    print(f"Creating project '{project_title}'...")
    project_id = create_project(token, owner_id, project_title)
    print(f"Created project with ID: {project_id}")

    for field_name, field_type, options in ROOT_FIELDS:
        print(f"  Creating field '{field_name}' ({field_type})...")
        try:
            if field_type == "SINGLE_SELECT":
                create_single_select_field(token, project_id, field_name, options or [])
            else:
                create_field(token, project_id, field_name, field_type)
        except Exception as e:
            print(f"    Warning: {e}")

    print(f"\nProject board created successfully.")
    print(f"PROJECT_ID:{project_id}")


if __name__ == "__main__":
    main()
