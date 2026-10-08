# Workflows

| Workflow | File | Schedule | Purpose |
|----------|------|----------|---------|
| Initiative Sync | `initiative-sync.yml` | Fridays 06:00 UTC | Updates risk register, STATUS.md, and project board per initiative |
| Standup Update | `standup-update.yml` | Daily 22:00 UTC | Writes STANDUP.md per pod from last 24h issue activity |
| Program Dashboard | `program-dashboard.yml` | Mondays 08:00 UTC | Regenerates PROGRAM-DASHBOARD.md across all initiatives |
| Program Changelog | `program-changelog.yml` | Fridays 17:00 UTC | Prepends weekly section to PROGRAM-CHANGELOG.md |
| Risk Aggregator | `risk-aggregator.yml` | Mon/Wed/Fri 07:00 UTC | Regenerates cross-initiative PROGRAM-RISKS.md |
| Risk Flag | `risk-flag.yml` | On issue labeled `blocked`/`dependency` | Appends risk row, posts comment, flags project board item |
| ADR Lint | `adr-lint.yml` | On PR touching config or pod README | Fails if architecture files changed without DECISION-LOG.md update |
