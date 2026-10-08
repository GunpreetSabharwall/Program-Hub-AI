# Feature 12 — Bottleneck Prediction

## What It Does

Every Friday at 06:45 UTC, for each initiative: reads the full open issue list with metadata (age, labels, assignee, comment count), reads recently closed blocked issues as historical patterns, reads velocity from STATUS.md. Calls Claude with prompt caching to predict which open issues are most likely to become blockers in the next 7 days. Adds a "Predicted Risks — Next 7 Days" section to PROGRAM-RISKS.md.

## System Prompt (Cached)

The system prompt is sent with `"cache_control": {"type": "ephemeral"}`. It is identical for every initiative call in a run, so it is cached after the first call.

```
You are a program manager with deep engineering experience.
Your task is to predict which open issues are most likely to become blockers in the next 7 days,
based on issue metadata and historical patterns.

Signals that predict future blockers:
- Issue age > 10 days with no comments (stale)
- Issue assigned to a person who has other blocked issues
- Issue title mentions API contract, external dependency, or cross-team work
- Issue has been re-opened or has many comments (contested)
- Issue is near the end of a sprint and has low comment activity
- Similar issues in closed history that became blocked

For each initiative, return a JSON array of at-risk issues (maximum 5):
[{"issue_number": N, "title": "...", "reason": "one sentence explaining why this is at risk",
  "confidence": "high|medium|low"}, ...]

Return JSON only — no markdown, no explanation. Return [] if no issues are at risk.
```

## User Prompt (Per Initiative)

```
Initiative: {name}
Velocity: {velocity} issues closed last week
Weeks to showcase: {weeks_remaining}

Open issues:
#{number}: {title} [age={N}d, comments={N}, assignee={login}, labels={labels}]
...

Recently closed issues (for pattern reference):
...

Which open issues are most likely to become blockers in the next 7 days?
```

## Prompt Caching

The system prompt is large and stable. By marking it `cache_control: ephemeral`, it is cached after the first API call. All subsequent initiative calls in the same run hit the cache, reducing cost by up to 90% on the system prompt tokens.

## Output Table Example

| Initiative | Issue | Confidence | Prediction |
|---|---|---|---|
| Example Initiative | octocat/example-app#42 Resolve auth API contract | High | This issue has been open 18 days with no comments and involves a cross-team API contract — a historically reliable blocker signal. |

## How to Enable

1. Ensure `OCTO_PAT` and `ANTHROPIC_API_KEY` secrets are set.
2. Workflow runs every Friday at 06:45 UTC, after the dependency graph (06:30 UTC).
3. Runs before the Monday dashboard refresh picks up the latest risk picture.
