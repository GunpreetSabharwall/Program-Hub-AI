# Scripts

| Script | Purpose |
|--------|---------|
| `onboard-initiative.py` | Interactive CLI: creates all governance files, pod folders, labels, project board, updates registries |
| `update-status.py` | Reads closed/blocked issues; writes STATUS.md with health signal |
| `update-risk-register.py` | Reads blocked + dependency issues; writes full RISK-REGISTER.md |
| `append-risk-register.py` | Appends a single risk row to RISK-REGISTER.md without overwriting |
| `update-pod-standups.py` | Reads issues by pod label; writes STANDUP.md per pod |
| `update-program-dashboard.py` | Reads all initiative configs; writes PROGRAM-DASHBOARD.md |
| `update-program-changelog.py` | Reads all configs; prepends weekly section to PROGRAM-CHANGELOG.md |
| `update-program-risks.py` | Reads all configs; writes cross-initiative PROGRAM-RISKS.md sorted by age |
| `flag-project-risk.py` | Sets Risk Level field on GitHub Project board item via GraphQL |
| `sync-project-board.py` | Adds open issues to project board; sets fields from config |
| `setup-project-board.py` | Creates GitHub Project with 8 custom fields |

## Setup

```bash
pip install pyyaml requests
```

All scripts read `OCTO_PAT` (or `GITHUB_TOKEN`) from the environment.
AI scripts additionally read `ANTHROPIC_API_KEY`.
