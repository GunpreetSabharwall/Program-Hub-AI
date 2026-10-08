# Feature 16 — Showcase Forecast

## What It Does

Every Monday at 08:45 UTC, computes a confidence score for each initiative reaching its showcase date on time. Calls Claude for a one-line explanation of each score. Adds a "Showcase Confidence" section to PROGRAM-DASHBOARD.md.

## The Math

```
confidence = min(100, (closure_rate × weeks_remaining / open_issues) × 100)
```

Where:
- `closure_rate` = issues closed last 7 days (from STATUS.md)
- `weeks_remaining` = calendar days until showcase_date ÷ 7
- `open_issues` = current open issue count (GitHub search API)

## Prompt

```
{initiative_name}: {open_issues} open issues, closing {closure_rate}/week,
{weeks_remaining} weeks to showcase, confidence score {confidence}%.
Write one sentence explaining this forecast for a program manager.
Output only the sentence.
```

## Output Example

Showcase Confidence section in PROGRAM-DASHBOARD.md:

| Initiative | Confidence | Assessment |
|---|---|---|
| Example Initiative | 78% | At the current closure rate of 3 issues/week with 12 weeks remaining, approximately 36 of the 46 open issues should close before the showcase date, making on-time delivery probable but not certain. |

## How to Enable

1. Ensure `showcase_date` is set in each initiative's `config.yml`.
2. Ensure `OCTO_PAT` and `ANTHROPIC_API_KEY` secrets are set.
3. Workflow runs every Monday at 08:45 UTC.
