# Feature Matrix

## Features 1–11 — Live (No AI Required)

All live features use only GitHub REST API and GraphQL. Dependencies: `pip install pyyaml requests`.

| # | Feature | Script | Trigger | Implementation |
|---|---------|--------|---------|----------------|
| 1 | Weekly status sync | `update-status.py` | Friday cron (initiative-sync.yml) | Queries closed issues (last 7 days) + blocked/dependency open issues. Calculates sprint week from `week_start`. Writes STATUS.md with health signal: Green (0 blockers), Amber (1-2), Red (3+). Preserves PM narrative block. |
| 2 | Risk register update | `update-risk-register.py` | Friday cron (initiative-sync.yml) | Queries blocked + dependency open issues. Deduplicates by issue number. Sorts by days open descending. Writes full RISK-REGISTER.md. |
| 3 | Real-time risk flagging | `append-risk-register.py` + `risk-flag.yml` | `issues: labeled` event in source repo | Appends single row to RISK-REGISTER.md without overwriting. Checks for duplicate by issue URL. Posts comment linking to risk register. Workflow is a template to copy into source repos. |
| 4 | Pod standup generation | `update-pod-standups.py` | Daily 22:00 UTC (standup-update.yml) | Queries issues per pod label: Done=closed last 24h, In Progress=open not blocked, Blocked=open+blocked label. Writes STANDUP.md per pod under `initiatives/<slug>/pods/<pod-slug>/`. |
| 5 | Program dashboard | `update-program-dashboard.py` | Monday 08:00 UTC (program-dashboard.yml) | Reads all `initiatives/*/config.yml`. Queries open issue count + blocked count per source repo via GitHub search API. Writes PROGRAM-DASHBOARD.md with health table. Flags initiatives needing PM attention. |
| 6 | Program changelog | `update-program-changelog.py` | Friday 17:00 UTC (program-changelog.yml) | Reads all configs. Queries closed issues this week + open blockers per initiative. Prepends new `## Week of YYYY-MM-DD` section. Leaves `<!-- PM: add narrative -->` placeholder. |
| 7 | Cross-initiative risk table | `update-program-risks.py` | Mon/Wed/Fri 07:00 UTC (risk-aggregator.yml) | Reads all configs. Queries blocked + dependency issues per source repo. Writes PROGRAM-RISKS.md sorted by age (oldest first). |
| 8 | Project board sync | `sync-project-board.py` | Friday cron (initiative-sync.yml) | Adds all open issues to GitHub Project V2 if not present. Sets Pod, Initiative, Start Date, End Date fields from config. Does NOT overwrite Sprint, Showcase Ready, Dependency On. |
| 9 | Project board risk flag | `flag-project-risk.py` | risk-flag.yml (issues: labeled) | Finds matching `github_project_id` from initiative configs. Sets Risk Level field: High=blocked, Medium=dependency. Uses GraphQL mutations. |
| 10 | ADR lint gate | `adr-lint.yml` | pull_request paths: `initiatives/**/config.yml`, `initiatives/**/pods/**/README.md` | Checks which initiatives have architecture file changes. Fails if `DECISION-LOG.md` was not also modified in the same PR. |
| 11 | Initiative onboarding CLI | `onboard-initiative.py` | Manual (`python scripts/onboard-initiative.py`) | Interactive prompts. Creates config.yml, STATUS.md, RISK-REGISTER.md, DECISION-LOG.md, pod STANDUP.md files. Creates blocked/dependency/adr-required + pod labels in source repo. Runs setup-project-board.py. Updates INITIATIVE-REGISTRY.md and README.md. Adds slug to workflow matrices. |

## Features 12–21 — AI-Enhanced

All AI features use `MODEL = "claude-sonnet-4-6"` via the Anthropic Python SDK. Additional dependency: `pip install anthropic`. All require `ANTHROPIC_API_KEY` env var.

Features are ordered simplest to most complex.

| # | Feature | Script | Trigger | Implementation |
|---|---------|--------|---------|----------------|
| 12 | Bottleneck prediction | `ai/feature-12-bottleneck-prediction/bottleneck-prediction.py` | Friday 06:45 UTC | Full open issue list (age/labels/assignee/comments) + recently closed blocked issues as history + velocity from STATUS.md. Calls Claude with **prompt caching** (`cache_control: {"type": "ephemeral"}` on system prompt). Returns JSON array of predicted-at-risk issues (max 5 per initiative). Adds "Predicted Risks — Next 7 Days" section to PROGRAM-RISKS.md. |
| 13 | Velocity anomaly detection | `ai/feature-13-velocity-anomaly/velocity-anomaly.py` | Monday 08:15 UTC | Reads STATUS.md files across last 4 weeks (git log). Computes rolling average of closed issues per pod. Flags pods >30% below baseline. Calls Claude for one-sentence explanation. Adds "Velocity Signal" column to PROGRAM-DASHBOARD.md. Green=within 30%, Amber=30-50% below, Red=>50% below or zero. |
| 14 | Dependency graph | `ai/feature-14-dependency-graph/dependency-graph.py` | Friday 06:30 UTC | Reads all open issues across all source repos. For each pair of initiatives, calls Claude with **prompt caching** on system prompt to identify coupled issue pairs. Writes `program/DEPENDENCY-MAP.md` with dependency pairs table. |
| 15 | Risk narratives | `ai/feature-15-risk-narratives/risk-narratives.py` | Monday 07:15 UTC | Reads PROGRAM-RISKS.md. Calls Claude to write 4-sentence executive summary of top 3 risks. Prepends "PM Digest" section above risk table. |
| 16 | Showcase forecast | `ai/feature-16-showcase-forecast/showcase-forecast.py` | Monday 08:45 UTC | Open issues (GitHub search), closure_rate from STATUS.md, weeks_remaining from showcase_date. Confidence = min(100, (closure_rate × weeks_remaining / open_issues) × 100). Calls Claude for one-line explanation. Adds "Showcase Confidence" column to PROGRAM-DASHBOARD.md. |
| 17 | Natural-language issue creation | `ai/feature-17-nl-issue-creation/nl-issue-creation.py` | Manual CLI | Takes initiative-slug and free text. Calls Claude to parse into {title, description, pod_label, is_blocked, is_dependency}. Creates GitHub Issue with correct labels. |
| 18 | Stale issue coach | `ai/feature-18-stale-issue-coach/stale-issue-coach.py` | Monday 09:00 UTC | Scans all source repos for issues open >14 days with zero comments. For each stale issue, calls Claude for 1-sentence nudge comment. Posts comment via GitHub API. |
| 19 | Meeting-to-issues | `ai/feature-19-meeting-to-issue/meeting-to-issue.py` | Manual CLI | Reads meeting notes file or stdin. Calls Claude to extract action items as JSON array [{title, description, assignee, initiative, is_blocked, is_dependency}]. Creates GitHub Issues in batch. |
| 20 | Blocker resolver | `ai/feature-20-blocker-resolver/blocker-resolver.py` | risk-flag.yml (blocked label) or manual | Takes repo + issue number. Reads issue title/description. Fetches last 50 closed issues for context. Calls Claude for 2-3 resolution suggestions + recommended owner + similar resolved issue. Posts comment. |
| 21 | PM briefing | `ai/feature-21-pm-briefing/pm-briefing.py` | Monday 08:30 UTC | Reads PROGRAM-DASHBOARD.md + PROGRAM-RISKS.md + latest changelog week section. Calls Claude for 5-sentence Slack briefing. Posts to Slack via SLACK_WEBHOOK_URL. |
