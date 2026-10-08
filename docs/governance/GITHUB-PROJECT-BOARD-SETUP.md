# GitHub Project Board Setup

Program Hub creates and manages a GitHub Project V2 board per initiative. The board is created automatically by `scripts/setup-project-board.py` when you run `scripts/onboard-initiative.py`.

## Custom Fields

| Field | Type | Owner | Automation notes |
|-------|------|-------|-----------------|
| Pod | Single Select | Automation-owned | Set by `sync-project-board.py` from issue pod label. Options created at onboarding. |
| Initiative | Single Select | Automation-owned | Set by `sync-project-board.py` from `config.yml name`. |
| Risk Level | Single Select | Automation-owned | Set by `flag-project-risk.py`: High=blocked, Medium=dependency. Never manually set. |
| Sprint | Text | Manual | Set by PM or engineer. Never overwritten by automation. |
| Start Date | Date | Automation-owned | Set to `week_start` from config. |
| End Date | Date | Automation-owned | Set to `showcase_date` from config. |
| Showcase Ready | Single Select | Manual | Set by engineer when feature is demo-ready. Never overwritten by automation. |
| Dependency On | Text | Manual | Free-text note on external dependency. Never overwritten by automation. |

**Automation-owned** means the field is written programmatically and should not be edited by hand — the next sync will overwrite manual changes.

**Manual** means automation never touches the field. Engineers and PMs set these.

## Setup Command

```bash
# Run automatically by onboard-initiative.py, or manually:
python scripts/setup-project-board.py <owner-login> "<Project Title>"
```

The script outputs `PROJECT_ID:<id>` on success. Copy that ID into `initiatives/<slug>/config.yml` under `github_project_id:`.

## How Items Get Added

Issues are added to the project board by `sync-project-board.py`, which runs every Friday as part of `initiative-sync.yml`. It queries all open issues in the source repository and calls the GitHub GraphQL `addProjectV2ItemById` mutation for any issue not already on the board.

Issues can also be added manually via the GitHub Project UI. The automation will set fields on newly added issues the next time the sync workflow runs.

## Real-Time Risk Flagging

When a `blocked` or `dependency` label is applied to an issue in the source repository, `risk-flag.yml` calls `flag-project-risk.py`, which:

1. Finds the matching `github_project_id` from initiative configs.
2. Adds the issue to the project board if not already present.
3. Sets the Risk Level field: High for `blocked`, Medium for `dependency`.

This happens within seconds of the label being applied, so the project board reflects the current risk state in real time without waiting for the Friday sync.

## Field Option Values

### Risk Level
- `High` — issue is labeled `blocked`
- `Medium` — issue is labeled `dependency`
- `Low` — default; set manually for issues with elevated but not yet labeled risk

### Showcase Ready
- `Yes` — feature complete and demo-ready
- `No` — not started or in progress
- `In Progress` — partially complete
