# Feature 21 — PM Briefing

## What It Does

Every Monday at 08:30 UTC, reads the current PROGRAM-DASHBOARD.md, PROGRAM-RISKS.md, and the latest weekly section of PROGRAM-CHANGELOG.md. Calls Claude to write a 5-sentence Slack briefing covering program health, what shipped, current blockers, what needs PM attention, and one concrete action for the week. Posts the briefing to Slack via webhook.

## Prompt

```
You are a program manager writing a Monday morning Slack briefing.

Program Dashboard:
{dashboard_text}

Program Risks:
{risks_text}

This Week's Changelog:
{changelog_text}

Write exactly 5 sentences suitable for posting in a Slack channel.
Cover: overall program health, what shipped last week, current blockers,
what needs PM attention, and one concrete action for this week.
Be specific with initiative names and numbers.
Output only the 5 sentences.
```

## Output Example

> :bar_chart: **Program Hub — Weekly Briefing (2026-06-25)**
>
> The program is in Green health overall with Example Initiative entering week 2 of 8 and 3 issues shipped last week. The auth API dependency (octocat/example-app#42) flagged on 2026-06-22 is the only active blocker and has been open 3 days without an update. No other initiatives are currently blocked or behind schedule. The platform team should be contacted today to confirm the auth contract timeline before it begins to threaten the 2026-08-13 showcase date. This week's priority action: schedule a 30-minute sync between @example-owner and the platform team lead to resolve the API contract.

## Value figures (Feature 22)

For initiatives with AEV turned on, the prompt also gets exact value figures (AEV CPI vs. classic EVM CPI, forecast, agent PR share, agent spend plus review, rework, CPI by pod × authorship) and is asked to say plainly when delivery and value disagree, and not to invent numbers.

## Running it by hand

```bash
python ai/feature-21-pm-briefing/pm-briefing.py --print            # print instead of posting to Slack
python ai/feature-21-pm-briefing/pm-briefing.py --print --no-ai    # fixed template, no API call
python ai/feature-21-pm-briefing/pm-briefing.py --print \
  --aev-json lakeshore-supplier-portal=demo/lakeshore/aev-after-revert.json
```

If the API call fails, the script prints the error and falls back to the fixed template, so a briefing is always produced.

## How to Enable

1. Create a Slack incoming webhook at api.slack.com/apps → Incoming Webhooks.
2. Add the webhook URL as `SLACK_WEBHOOK_URL` in GitHub Actions secrets.
3. Add `ANTHROPIC_API_KEY` secret.
4. The workflow runs every Monday at 08:30 UTC, after the dashboard and risk scripts have run.
