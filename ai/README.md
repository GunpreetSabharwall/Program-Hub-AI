# AI Features

Program Hub's AI features (12–21) add interpretation, prediction, and natural-language interfaces on top of the live automation features (1–11). They are all optional enhancements — the live features work without any AI API key.

## Setup

```bash
pip install anthropic pyyaml requests
```

Set the `ANTHROPIC_API_KEY` environment variable (or GitHub Actions secret).

All AI features use `MODEL = "claude-sonnet-4-6"`.

## Feature Table (simplest to most complex)

| # | Feature | Folder | Schedule | What it produces |
|---|---------|--------|----------|-----------------|
| 12 | Bottleneck prediction | `feature-12-bottleneck-prediction/` | Friday 06:45 UTC | Predicted-at-risk issues section in PROGRAM-RISKS.md |
| 13 | Velocity anomaly detection | `feature-13-velocity-anomaly/` | Monday 08:15 UTC | Velocity Signal column in PROGRAM-DASHBOARD.md |
| 14 | Dependency graph | `feature-14-dependency-graph/` | Friday 06:30 UTC | program/DEPENDENCY-MAP.md |
| 15 | Risk narratives | `feature-15-risk-narratives/` | Monday 07:15 UTC | PM Digest section in PROGRAM-RISKS.md |
| 16 | Showcase forecast | `feature-16-showcase-forecast/` | Monday 08:45 UTC | Showcase Confidence column in PROGRAM-DASHBOARD.md |
| 17 | NL issue creation | `feature-17-nl-issue-creation/` | Manual CLI | New GitHub Issue from free text |
| 18 | Stale issue coach | `feature-18-stale-issue-coach/` | Monday 09:00 UTC | Nudge comment on stale issues |
| 19 | Meeting-to-issues | `feature-19-meeting-to-issue/` | Manual CLI | Batch GitHub Issues from meeting notes |
| 20 | Blocker resolver | `feature-20-blocker-resolver/` | risk-flag.yml / manual | Resolution suggestions comment on blocked issue |
| 21 | PM briefing | `feature-21-pm-briefing/` | Monday 08:30 UTC | Slack message with 5-sentence program summary |

## Prompt Caching

Features 12 (bottleneck prediction) and 14 (dependency graph) process large, repeated context windows (full issue backlogs). Both use Anthropic prompt caching by adding `"cache_control": {"type": "ephemeral"}` to the system prompt. This reduces latency and cost on repeated runs against the same data snapshot.

See each feature's README for the specific system prompt used.
