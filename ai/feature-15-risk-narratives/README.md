# Feature 15 — Risk Narratives

## What It Does

Every Monday at 07:15 UTC, reads `program/PROGRAM-RISKS.md` and calls Claude to write a 4-sentence executive summary of the top 3 risks. Prepends a "PM Digest" section above the risk table.

## Prompt

```
You are a program manager writing an executive summary.

Below is a program risk table:

{risks_table}

Write exactly 4 sentences summarising the top 3 risks for a VP-level reader.
Focus on business impact and urgency, not technical detail.
Name the specific initiatives and issues involved.
Output only the 4 sentences, no headings or bullet points.
```

## Output Example

PM Digest section prepended to PROGRAM-RISKS.md:

> ## PM Digest
>
> *AI-generated executive summary — 2026-06-25*
>
> The most pressing risk is a dependency block in Example Initiative (#42) where the auth API contract with the platform team has been unresolved for 3 days, directly gating the login flow milestone. If unresolved by end of week, the showcase date of 2026-08-13 is at risk given only 7 weeks remain. No other initiatives currently carry open blockers. The platform team dependency should be escalated to the engineering director by Wednesday if the API contract is not signed by Monday EOD.

## How to Enable

1. Ensure `ANTHROPIC_API_KEY` secret is set.
2. Workflow runs automatically every Monday at 07:15 UTC.
3. Runs after the risk aggregator (07:00 UTC) so the digest reflects the latest risk table.
