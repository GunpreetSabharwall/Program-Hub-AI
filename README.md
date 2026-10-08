# Program Hub AI

Program Hub is a GitHub-native program governance framework that eliminates the translation layer between engineering work and program-management reporting. Each initiative lives in a YAML config file; a set of scheduled GitHub Actions workflows reads that config, queries the initiative's source repository for issues, and automatically regenerates status documents, risk registers, pod standups, and a cross-initiative program dashboard — all as Markdown files committed to this repository. Program managers get a single place to read the current health of every initiative without asking engineers to fill in spreadsheets, and engineers keep working in GitHub Issues exactly as they always have.

## Active Initiatives

| Slug | Name | Owner | Status | Showcase Date |
|------|------|-------|--------|---------------|
| example-initiative | Example Initiative | @example-owner | active | 2026-08-13 |

## Feature Matrix

### Features 1–11 — Live

| # | Feature | Description |
|---|---------|-------------|
| 1 | Weekly status sync | Reads closed/blocked issues; writes STATUS.md with health signal |
| 2 | Risk register update | Writes RISK-REGISTER.md from blocked + dependency issues |
| 3 | Real-time risk flagging | On `blocked`/`dependency` label event: appends risk row, posts comment |
| 4 | Pod standup generation | Daily: writes STANDUP.md per pod from filtered issues |
| 5 | Program dashboard | Weekly: writes PROGRAM-DASHBOARD.md across all initiatives |
| 6 | Program changelog | Weekly: prepends new section to PROGRAM-CHANGELOG.md |
| 7 | Cross-initiative risk table | Tri-weekly: writes PROGRAM-RISKS.md sorted by age |
| 8 | Project board sync | Adds open issues to GitHub Project; sets Pod/Initiative/dates |
| 9 | Project board risk flag | Sets Risk Level field on board item via GraphQL |
| 10 | ADR lint gate | PR check: architecture changes require DECISION-LOG.md update |
| 11 | Initiative onboarding CLI | Interactive script: creates all governance files, pod labels, project board |

### Features 12–21 — AI-Enhanced

| # | Feature | Description |
|---|---------|-------------|
| 12 | Bottleneck prediction | Predicts issues likely to block in next 7 days (prompt caching) |
| 13 | Velocity anomaly detection | Flags pods >30% below 4-week baseline; explains anomaly |
| 14 | Dependency graph | Identifies coupled issue pairs across initiatives (prompt caching) |
| 15 | Risk narratives | Writes 4-sentence executive summary of top 3 risks |
| 16 | Showcase forecast | Estimates on-track confidence per initiative with explanation |
| 17 | Natural-language issue creation | CLI: free text → structured GitHub Issue |
| 18 | Stale issue coach | Weekly: posts 1-sentence nudge on issues stale >14 days |
| 19 | Meeting-to-issues | Reads meeting notes; extracts and creates action-item issues in batch |
| 20 | Blocker resolver | On blocked label: posts 2-3 resolution suggestions + owner recommendation |
| 21 | PM briefing | Monday: posts 5-sentence Slack briefing from dashboard + risks + changelog |

## How It Works

Each initiative is described by a single `initiatives/<slug>/config.yml` file. Workflows read that config to know which GitHub repository to query, which labels map to pods and risk states, and what the sprint timeline looks like. All generated Markdown files carry an "auto-regenerated" notice at the top — program managers edit only the PM narrative placeholders, never the data rows. Adding a new initiative means running `scripts/onboard-initiative.py`, answering a handful of prompts, and merging the resulting PR.

## Quick Start

```bash
# 1. Clone this repository
git clone https://github.com/GunpreetSabharwall/Program-Hub-AI.git
cd Program-Hub-AI

# 2. Add repository secrets in GitHub Settings → Secrets and variables → Actions
#    OCTO_PAT, ANTHROPIC_API_KEY, SLACK_WEBHOOK_URL  (see Required secrets below)

# 3. Onboard your first initiative
pip install pyyaml requests
python scripts/onboard-initiative.py

# 4. Done — workflows run on their schedule or via workflow_dispatch
```

## Required Secrets

| Secret | Used by | Purpose |
|--------|---------|---------|
| `OCTO_PAT` | All live workflows | Read issues, write project board fields, create labels |
| `ANTHROPIC_API_KEY` | All AI features | Call Claude via Anthropic API |
| `SLACK_WEBHOOK_URL` | Feature 21 PM briefing | Post weekly Slack briefing |

## AI Features

AI features (12–21) are implemented as standalone scripts under `ai/`. They all use model `claude-sonnet-4-6` via the Anthropic Python SDK (`pip install anthropic`). Features 12 (bottleneck prediction) and 14 (dependency graph) use prompt caching (`cache_control: {"type": "ephemeral"}`) on their system prompts to reduce latency and cost on repeated runs.

Feature 14 writes a cross-initiative dependency map to `program/DEPENDENCY-MAP.md` every Friday. This file is the single place to see which issues in different initiatives are coupled, so a slip in one repo surfaces immediately as a risk in the other.

## Further Reading

- [Rollout and Adoption Plan](docs/ROLLOUT-AND-ADOPTION-PLAN.md)
- [Full Feature Matrix](docs/FEATURE-MATRIX.md)
- [GitHub Project Board Setup](docs/governance/GITHUB-PROJECT-BOARD-SETUP.md)
