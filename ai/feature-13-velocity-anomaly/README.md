# Feature 13 — Velocity Anomaly Detection

## What It Does

Every Monday at 08:15 UTC, reads STATUS.md files from git history to compute a 4-week rolling average of closed issues per pod. Flags pods more than 30% below their baseline. Calls Claude to write a one-sentence explanation of the anomaly. Adds a "Velocity Signal" section to PROGRAM-DASHBOARD.md.

## Classification Logic

| Signal | Condition |
|--------|-----------|
| 🟢 Green | Current week within 30% of 4-week average |
| 🟡 Amber | Current week 30–50% below 4-week average |
| 🔴 Red | Current week >50% below 4-week average, or zero issues closed |

Formula: `pct_below = (baseline - current) / baseline`

## Prompt

```
Program management context: {pod_name} in {initiative_name} closed {current} issues this week.
Their 4-week average is {baseline} issues/week.
Weekly history (oldest first): {history}.

Write one sentence explaining the most likely cause of this velocity change.
Be concrete. Output only the sentence.
```

## Output Example

Velocity Signal column in PROGRAM-DASHBOARD.md:

| Initiative | Pod | This Week | 4-Week Avg | Signal | Note |
|---|---|---|---|---|---|
| Example Initiative | Example Pod | 1 | 3.7 | 🔴 Red | The pod appears to have shifted focus to the auth integration milestone, which generated fewer closable discrete tasks than the previous infrastructure sprint. |

## How to Enable

1. Ensure `ANTHROPIC_API_KEY` secret is set.
2. Workflow runs automatically every Monday. Trigger via workflow_dispatch to test.
3. Requires `fetch-depth: 20` in checkout action to access git history for STATUS.md.
