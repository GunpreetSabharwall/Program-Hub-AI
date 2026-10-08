# Feature 14 — Dependency Graph

## What It Does

Every Friday at 06:30 UTC, reads all open issues across all source repositories. For each pair of initiatives, calls Claude to identify issue pairs that are likely coupled across initiative boundaries. Writes `program/DEPENDENCY-MAP.md`.

## System Prompt (Cached)

The system prompt is sent with `"cache_control": {"type": "ephemeral"}` so that the large, stable prompt is cached server-side. This reduces cost and latency on repeated runs.

```
You are a program manager analysing GitHub issues across multiple engineering initiatives.
Your task is to identify pairs of issues from DIFFERENT initiatives that are likely coupled...

Coupling signals to look for:
- Shared API or interface contracts
- One issue explicitly references another team's work
- Same data model or schema changes needed by both
- Shared infrastructure or service dependency
- Authentication, authorisation, or identity flows touched by both
- Explicit "waiting on X team" language

Return a JSON array of coupled pairs:
[{"initiative_a": "...", "issue_a": "#N title", "initiative_b": "...", "issue_b": "#N title",
  "reason": "one sentence explaining the coupling", "severity": "high|medium|low"}, ...]

Return [] if no coupling is found. Return JSON only — no markdown, no explanation.
```

## User Prompt (Per Pair)

```
Initiative A: {name_a}
Open issues:
{issues_a}

Initiative B: {name_b}
Open issues:
{issues_b}

Identify coupled issue pairs between these two initiatives.
```

## Prompt Caching

The system prompt is identical for every initiative pair call in a run. By marking it with `cache_control: ephemeral`, Anthropic caches it after the first call in a session. Subsequent calls in the same run hit the cache, reducing per-call cost by up to 90% on the prompt tokens.

## Output Table Example

| Severity | Initiative A | Issue A | Initiative B | Issue B | Reason |
|---|---|---|---|---|---|
| High | Example Initiative | #42 Resolve auth API contract | Platform Initiative | #17 Publish auth service contract | Both issues must align on the same API contract before either can close. |

## How to Enable

1. Ensure `OCTO_PAT` and `ANTHROPIC_API_KEY` secrets are set.
2. Workflow runs every Friday at 06:30 UTC. Trigger via workflow_dispatch to test.
3. Requires at least 2 initiatives in `initiatives/` to produce output.
