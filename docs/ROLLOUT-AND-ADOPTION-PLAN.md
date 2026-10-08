# Rollout and Adoption Plan

## Phases

### Phase 1 — Pilot (Weeks 1–2)

**Goal:** Validate that live features work end-to-end with one real initiative.

| Step | Owner | Done when |
|------|-------|-----------|
| Run `onboard-initiative.py` for one initiative | PM | Config file merged, labels created in source repo |
| Add `OCTO_PAT` secret to this repository | Repo admin | Workflow can query source repo |
| Trigger `initiative-sync` via workflow_dispatch | PM | STATUS.md and RISK-REGISTER.md populated with real data |
| Trigger `standup-update` via workflow_dispatch | PM | STANDUP.md populated for each pod |
| Review generated documents with engineering lead | PM + Eng | Both parties agree documents are accurate |
| Trigger `program-dashboard` via workflow_dispatch | PM | PROGRAM-DASHBOARD.md reflects real initiative state |

**Success signal:** PM reads PROGRAM-DASHBOARD.md on Monday morning with accurate data, zero manual steps required.

### Phase 2 — Validate (Weeks 3–4)

**Goal:** Confirm schedules run reliably; enable AI features; gather feedback.

| Step | Owner | Done when |
|------|-------|-----------|
| Confirm all scheduled workflows ran without failure | PM | GitHub Actions history shows green runs |
| Add `ANTHROPIC_API_KEY` secret | Repo admin | AI workflows enabled |
| Add `SLACK_WEBHOOK_URL` secret | Repo admin | PM briefing posts to Slack |
| Enable AI workflows via workflow_dispatch | PM | Features 12–21 produce output |
| Review AI feature output quality | PM + Eng | At least 3 of 10 AI features deemed useful |
| File issues for any inaccurate or unhelpful AI output | PM | Issues logged in this repo |

**Success signal:** At least one PM reports that AI-generated output (blocker resolver, risk narratives, or PM briefing) saved them time relative to writing it manually.

### Phase 3 — Expand (Weeks 5–8)

**Goal:** Onboard remaining initiatives; establish steady-state operation.

| Step | Owner | Done when |
|------|-------|-----------|
| Onboard remaining initiatives | PM | Each initiative has config.yml, STATUS.md, RISK-REGISTER.md |
| Copy risk-flag.yml to each source repo | Eng leads | Blocked/dependency label events fire Program Hub workflows |
| Review DECISION-LOG.md workflow in practice | Eng | First PR blocked by ADR lint gate and resolved correctly |
| Establish weekly PM review cadence | PM | Recurring calendar hold: 15 min Monday to read dashboard |
| Deprecate manual status spreadsheets | PM | Spreadsheets archived with link to Program Hub |
| Retrospective on AI feature quality | PM + Eng | Features with low utility disabled; prompt tuning backlog created |

**Success signal:** All initiatives onboarded; no manual status spreadsheets in active use; PM can answer "what is the current program health?" from this repository alone.

## Adoption Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Source repo labels not applied consistently | Medium | High (risk register misses issues) | Label creation is automated at onboarding; ADR lint enforces label discipline |
| Engineers feel surveilled by standup automation | Medium | Medium (morale impact) | Frame as PM-facing tool, not engineer reporting; standups are generated not filed |
| GitHub API rate limits hit during large syncs | Low | Medium (workflow failure) | Scripts paginate and fail loudly; re-run via workflow_dispatch |
| AI output quality poor for specific initiative types | Medium | Low (features are additive, not critical path) | AI features are opt-in enhancements; live features work without AI API key |
| OCTO_PAT expires or is revoked | Low | High (all workflows fail) | Set calendar reminder before token expiry; use fine-grained PAT with minimal scope |
| PM narrative placeholders overwritten | Low | Medium (loss of written context) | Scripts preserve content between `<!-- PM: ... -->` markers; test on pilot before scaling |

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Zero manual status updates | No Markdown edits outside PM narrative blocks for 4 consecutive weeks |
| Dashboard accuracy | Engineering lead confirms dashboard matches their mental model of health in spot-checks |
| Blocker visibility | All issues labeled `blocked` appear in RISK-REGISTER.md within 5 minutes of labeling |
| PM time saved | PM self-reports spending <15 min/week on status reporting (vs. prior baseline) |
| AI feature utility | At least 50% of AI features rated "useful or better" in 4-week retrospective |
