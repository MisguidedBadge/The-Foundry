# AGENTS.md

## Repository Purpose

[Describe the product, project, or service in one paragraph.]

## Read-First Order

Before making changes, read these files when they exist:

1. `README.md`
2. `prd.md` or `[product source of truth]`
3. `TASK.md`
4. `supervisor_manual.md`
5. `guardrails.md`
6. `progress.md`

## Core Working Rules

- Implement only the active task described in `TASK.md`.
- Prefer the smallest change set that satisfies the task.
- Do not claim success unless required verification passes.
- When behavior changes, add or update tests.
- Treat existing uncommitted changes as user or prior-agent work.
- Do not revert unrelated changes unless explicitly requested.
- Do not edit secrets, credentials, or private key material.

## Default Verification

The default verifier is:

```bash
[default verifier command]
```

The default verifier must be deterministic and must not require live hardware,
private network access, cloud credentials, or manual operator input.

Optional live checks:

```bash
[optional live verifier command]
```

Optional live checks must skip by default unless explicitly enabled.

## Supervisor Discipline

When the user asks for subagents, delegated verification, Ralph loops, or
supervisory mode, the Codex session should supervise rather than becoming the
primary implementor.

In supervisory mode:

- delegate bounded exploration, implementation, and verification work
- avoid overlapping worker ownership
- poll active workers periodically
- close workers when complete
- review diffs before accepting worker output
- ground final judgment in verifier output

## Done Means

A task is done only when:

- requested behavior exists
- tests/checks pass
- docs match behavior
- default verifier remains deterministic
- optional live checks are either green or clearly reported as skipped/blocked
