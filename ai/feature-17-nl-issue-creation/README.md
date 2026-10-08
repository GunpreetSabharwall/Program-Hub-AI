# Feature 17 — Natural-Language Issue Creation

## What It Does

Takes an initiative slug and a free-text description of work that needs to happen. Calls Claude to parse the text into a structured issue with title, description, pod label, and risk flags. Creates the GitHub Issue with the correct labels applied.

## Usage

```bash
OCTO_PAT=... ANTHROPIC_API_KEY=... python ai/feature-17-nl-issue-creation/nl-issue-creation.py \
  example-initiative \
  "we need to sort out the auth handoff with the platform team before we can ship the login page"
```

## Prompt

```
Parse the following note into a structured GitHub issue.

Note: {free_text}

Available pod labels: {pod_labels}
Pod names: {pod_names}

Return JSON only (no markdown, no explanation):
{"title": "...", "description": "...", "pod_label": "..." or null,
 "is_blocked": true/false, "is_dependency": true/false}

title: clear, concise issue title (max 80 chars)
description: 1-3 sentences of context as GitHub issue body
pod_label: the most appropriate pod label from the list, or null
is_blocked: true if the note indicates this work is currently blocked
is_dependency: true if this represents a dependency on another team/system
```

## Output Example

Input:
> "we need to sort out the auth handoff with the platform team before we can ship the login page"

Parsed JSON:
```json
{
  "title": "Resolve auth API contract with platform team to unblock login page",
  "description": "The login page implementation is blocked on the platform team providing the auth API contract. This must be resolved before the login flow can be completed.",
  "pod_label": "pod1-example",
  "is_blocked": false,
  "is_dependency": true
}
```

Issue created with labels: `pod1-example`, `dependency`.

## How to Extend to a Slack Bot

Add a Slack slash command (e.g. `/issue example-initiative <text>`) that calls this script via a Lambda function or GitHub Actions workflow_dispatch with `inputs.text`. The script posts back the created issue URL.
