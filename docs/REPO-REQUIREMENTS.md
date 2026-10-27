# What a source repository needs

Program Hub governs initiatives whose work lives in other GitHub repositories (**source repos**). It reads each one from outside: nothing is installed in a source repo, and Program Hub never needs write access to it. Each initiative is one folder here, `initiatives/<slug>/`, pointing at one source repo.

When an initiative turns on the value signal (Feature 22), Program Hub also runs [Agentic Earned Value (AEV)](https://github.com/GunpreetSabharwall/agentic-earned-value) on the same source repo. AEV reads it from outside too, and gives its results back to Program Hub.

```
 source repo (read only)            Program Hub (this repo)
 ┌───────────────────────┐          initiatives/<slug>/
 │ issues, labels, PRs,  │──read──► config.yml ............ plan, pods, aev settings (you edit)
 │ commits               │          aev/hours.csv ......... human hours (you edit)
 └───────────────────────┘          aev/agent-costs.csv ... agent spend (you edit)
            │                       STATUS.md, RISK-REGISTER.md, pods/*/STANDUP.md  (Program Hub writes)
            └──────read by AEV────► aev/aev.json, aev/AEV-REPORT.md                  (AEV writes)
                                    VALUE.md, program/PROGRAM-DASHBOARD.md           (Program Hub writes)
```

## 1. For Program Hub (delivery: status, risks, standups, dashboard)

| # | Required in the source repo | How | Used by |
|---|---|---|---|
| 1 | Work is tracked as **GitHub Issues** | One issue per piece of work | Every feature |
| 2 | **Close issues when done** | Close, or merge a PR with `Fixes #N` | Status (closed this week), changelog, velocity |
| 3 | **Blocked work is labelled** | The label named in `labels.blocked` (default `blocked`) | Health signal, risk register, real-time risk flag |
| 4 | **Cross-team dependencies are labelled** | `labels.dependency` (default `dependency`) | Risk register, dependency map |
| 5 | **Each issue carries its pod's label** | The `label` of a pod in `pods:` | Pod standups, project board, velocity per pod |

Optional: assignees (bottleneck prediction, blocker resolver), a GitHub Project (`github_project_id`), `labels.adr` for architecture decisions. `scripts/onboard-initiative.py` creates the labels.

## 2. For AEV (value: cost, rework, attribution)

Everything in section 1, plus:

| # | Required in the source repo | How | Why |
|---|---|---|---|
| 6 | **Planned issues have a size label** | `aev-points:N`, for example `aev-points:3` | Budgeted value = N × `value_per_point`. Issues without it earn nothing |
| 7 | **Every pull request names its issue** | `Fixes #N` (finishes it) or `Part of #N` (partial work) in the PR description | Links cost and authorship to the issue |
| 8 | **Finished issues are closed as completed** | Not *closed as not planned* | Accepted = closed as completed and a linked PR merged |
| 9 | **Undo with GitHub's Revert button, or reopen the issue** | PR page → Revert, then merge the revert PR | AEV takes the value back if this happens within the stabilization window |
| 10 | **Agent work is recognisable** | PR label `aev-agent`, or an agent account opens the PR, or commits are authored or co-authored (`Co-authored-by:`) by an agent account | Splits value and cost into agent, human and mixed work |

Team breakdown comes for free: AEV uses the pod labels from item 5.

Full details, common mistakes and how to run AEV on its own: [AEV's REPO-REQUIREMENTS.md](https://github.com/GunpreetSabharwall/agentic-earned-value/blob/main/docs/REPO-REQUIREMENTS.md).

## 3. In Program Hub (kept by the PMO, not the engineering team)

`initiatives/<slug>/config.yml`:

```yaml
source_repo: my-org/supplier-portal
week_start: 2026-09-29        # AEV's plan starts here...
duration_weeks: 12            # ...and ends here
pods:                         # AEV's teams are these pods, matched by label
  - { slug: portal, label: pod-portal, name: Portal }
aev:                          # turns on the value signal (Feature 22)
  mode: hub                   # Program Hub runs AEV on source_repo
  budget_at_completion: 240000
  value_per_point: 2000
  hourly_rate: 100
  stabilization_window_days: 14     # optional, default 14
  agent_accounts: [coding-agent]    # optional
```

`initiatives/<slug>/aev/hours.csv` (`date,item,type,hours`, type `build` or `review`) and `aev/agent-costs.csv` (`date,item,category,amount[,tokens]`). `item` is the issue number in the source repo.

## 4. Access

One secret in this repository, **`OCTO_PAT`**, that can **read** every source repo. Recommended: a fine-grained personal access token (or a GitHub App) with read-only *Contents*, *Issues*, *Pull requests* and *Metadata* on the source repos.

Without it, Program Hub falls back to the workflow's built-in token, which reaches only this repository; public source repos can still be read anonymously through the REST API, but AEV reads through the GraphQL API, which needs a token with access. Set `OCTO_PAT`.

## Data flow, once a week (or on demand)

1. **Program Dashboard** workflow starts (Mondays, or Actions → Program Dashboard → Run workflow).
2. `scripts/run_aev.py`: for each initiative with `aev:`, builds AEV's settings from `config.yml` (budget, dates, pods), runs AEV on `source_repo` with the cost files from `aev/`, and writes `aev/aev.json` and `aev/AEV-REPORT.md`.
3. `scripts/aev_value.py`: writes `VALUE.md` from `aev/aev.json`.
4. `scripts/update-program-dashboard.py`: delivery health from the source repo's issues, value health from AEV, side by side.
5. Everything is committed here; Git history is the audit trail.

`aev.mode: repo` is the alternative for a team that already runs AEV inside its own repository: Program Hub then reads that repo's `.aev/aev.json` instead of running AEV itself.
