# Decision Log — Example Initiative

Architectural decisions affecting this initiative. Each entry corresponds to an issue or PR labeled `adr-required`.

| ADR | Title | Date | Status | Link |
|-----|-------|------|--------|------|
| ADR-001 | Adopt YAML config as single source of truth | 2026-06-18 | Accepted | — |

---

## ADR-001: Adopt YAML config as single source of truth

**Date:** 2026-06-18
**Status:** Accepted
**Deciders:** @example-owner

### Context

The initiative needs a canonical place to store metadata (owner, source repo, sprint dates, pod labels) that both humans and automation can read without ambiguity.

### Decision

Store all initiative metadata in `initiatives/<slug>/config.yml`. All scripts and workflows read this file. No metadata lives in workflow files or script constants.

### Consequences

- Adding a new initiative requires only a new config file and a run of `onboard-initiative.py`.
- Changing sprint dates, pod structure, or label names is a single-file YAML edit.
- Workflow matrices must be updated by `onboard-initiative.py` when a new initiative is added.
