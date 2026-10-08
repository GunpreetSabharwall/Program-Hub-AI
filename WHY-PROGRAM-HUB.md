# Why Program Hub?

## The Problem

Engineering teams track work in GitHub Issues. Program managers track work in spreadsheets, slide decks, and weekly status emails. The gap between the two creates a mechanical translation job: every Friday, engineers export data from GitHub and paste it into a dashboard someone else reads on Monday. That translation adds no value. It delays information, introduces transcription errors, and eats several hours of engineering time every week.

Program Hub removes that translation layer entirely.

## Design Principles

**Single source of truth.** Every status document, risk register, and standup is generated directly from GitHub Issues. There is no secondary data store. If the issue is closed, the status says closed. No manual sync required.

**Config over code.** Adding a new initiative means adding a YAML file and running one script. No workflow logic changes, no new Python, no infrastructure. The config expresses intent; the scripts handle mechanics.

**Git history as audit trail.** All generated documents live in this repository. Every change is a commit. Program managers can `git log` or `git diff` to see exactly what changed between last week and this week, who the last author was, and why.

**Automate the mechanical; narrate the judgment.** Workflows handle data collection, document generation, and project board updates. They leave clearly marked `<!-- PM: add narrative here -->` placeholders for the parts that require human judgment — escalation framing, stakeholder context, strategic interpretation.

**Fail loud.** If a workflow cannot reach the source repository or the API returns an unexpected response, the workflow fails visibly. Silent staleness is worse than a noisy failure.

## What AI Adds

The live features (1–11) are pure automation: deterministic queries, deterministic writes. They work without any AI API key.

The AI features (12–21) add a layer of interpretation on top of that data:

- **Pattern recognition across messy text.** GitHub issue titles and descriptions are free text. Claude can read a backlog of 200 issues and identify which pairs of issues in different repositories are likely coupled — a judgment call no regex can make reliably.
- **Anomaly explanation.** When velocity drops 40% in one pod, the raw number is visible in the dashboard. Claude reads the issue list for that pod and writes one sentence explaining the most likely cause — saving the PM from digging through 30 issue titles themselves.
- **Predictive risk.** Blocked issues that will surface next week look like normal open issues today. Claude reads issue age, label history, assignee workload, and sprint position to flag the ones most likely to become blockers before they are labeled.
- **Natural-language interfaces.** Engineering teams should not have to learn a governance taxonomy to create well-formed issues. Claude translates free text ("we need to sort out the auth handoff with the platform team before we can ship the login page") into a structured issue with the right pod label, the right dependency flag, and a clear title.

All AI features use `claude-sonnet-4-6`. Features with large, repeated context windows use prompt caching to keep costs low.
