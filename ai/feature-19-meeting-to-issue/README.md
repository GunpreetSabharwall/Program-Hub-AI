# Feature 19 — Meeting to Issues

## What It Does

Reads meeting notes from a file or stdin. Calls Claude to extract all action items, decisions, and commitments as a JSON array of structured issues. Creates GitHub Issues in batch with correct pod labels, assignees, and risk flags.

## Usage

```bash
# From a file
OCTO_PAT=... ANTHROPIC_API_KEY=... python ai/feature-19-meeting-to-issue/meeting-to-issue.py \
  example-initiative meeting-notes.txt

# From stdin
cat meeting-notes.txt | OCTO_PAT=... ANTHROPIC_API_KEY=... \
  python ai/feature-19-meeting-to-issue/meeting-to-issue.py example-initiative -
```

## Prompt

```
Extract all action items from the following meeting notes as GitHub issues.

Meeting notes:
{notes}

Available pod labels: {pod_labels}
Available initiatives: {initiative_names}

Return a JSON array only (no markdown, no explanation):
[{"title": "...", "description": "...", "assignee": "..." or null,
  "initiative": "..." or null, "pod_label": "..." or null,
  "is_blocked": true/false, "is_dependency": true/false}, ...]

Extract every concrete action item, decision, or commitment mentioned.
Use null for assignee/initiative/pod_label when not clear from context.
is_blocked: true if the action is currently blocked on something.
is_dependency: true if this action depends on another team or system.
```

## Output Example

Meeting notes snippet:
> Alice to implement the JWT middleware by Friday. Blocked on getting the signing keys from the security team. Bob to chase the platform team for the API schema — this is a dependency for three other features.

Issues created:
- `#44`: "Implement JWT middleware" — labels: `pod1-example`, `blocked`
- `#45`: "Obtain JWT signing keys from security team" — labels: (none)
- `#46`: "Obtain platform team API schema" — labels: `dependency`

## How to Enable

No workflow is needed for manual use. Run from the command line after any meeting.

To automate, add a workflow that accepts meeting notes as a workflow_dispatch input and calls this script.
