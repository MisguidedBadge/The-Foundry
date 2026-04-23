# Supervisor Manual

## Purpose

This project uses a supervisory Codex method for complex work. One supervisor
coordinates bounded workers, protects scope, reviews evidence, and makes final
judgments based on verification.

## Startup Checklist

At the start of a supervised session:

1. Read `AGENTS.md`.
2. Read `prd.md`.
3. Read `TASK.md`.
4. Read `progress.md` and `guardrails.md`.
5. Check `git status --short --branch`.
6. Identify the active scope and non-goals.
7. Decide what can be delegated safely.

## Delegation Rules

- Use explorers for read-only fact finding.
- Use implementation workers for bounded file ownership.
- Use verification workers for tests and evidence.
- Use live diagnostic workers for optional real-system checks.
- Do not assign overlapping write ownership.
- Tell every worker not to revert unrelated changes.
- Close workers after reviewing their result.

## Verification Rules

Required verification:

```bash
scripts/verify-live
```

Verification is intentionally live in this repository. Do not replace live
ROCm-backed checks with fake or virtual tests.

## Final Report

Include:

- changed behavior
- files or subsystems touched
- exact verification commands and outcomes
- optional live checks, if any
- residual risks
- commit/push status, if applicable

## Refinement Rule

When a supervised run teaches a repeatable lesson, update this manual or
`guardrails.md`.
