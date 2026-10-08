# Feature 18 — Stale Issue Coach

## What It Does

Every Monday at 09:00 UTC, scans all source repositories for issues that have been open for more than 14 days with zero comments. For each stale issue, calls Claude to generate a friendly one-sentence nudge specific to the issue content, then posts that nudge as a GitHub comment.

## Prompt

```
This GitHub issue has been open for {days_open} days with no comments:

Title: {issue_title}

Description: {issue_body_snippet}

Write a single friendly sentence to nudge the assignee to update the issue
or ask for help if needed. Be specific to the issue content.
Do not start with "I" or use the word "nudge". Output only the sentence.
```

## Output Example

> :alarm_clock: **Stale issue check-in** — this issue has been open for 17 days with no comments.
>
> Could you share a quick update on where the auth middleware implementation stands, or flag if you need an extra pair of hands on the JWT validation logic?
>
> *This comment was generated automatically by Program Hub.*

## How to Enable

1. Ensure `OCTO_PAT` and `ANTHROPIC_API_KEY` secrets are set in this repository.
2. The workflow runs automatically every Monday. Trigger manually via workflow_dispatch to test.
3. To disable for a specific initiative, remove its source repo from the scan by filtering in `stale-issue-coach.py`.
