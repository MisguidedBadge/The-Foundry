# Review And Integration

The supervisor's most important work happens after workers return. A worker
patch is not complete just because it exists. The supervisor must review scope,
behavior, tests, and evidence before integration.

## Review Order

Use this order:

1. Check `git status --short --branch`.
2. Inspect `git diff --stat`.
3. Review the actual diff for changed files.
4. Compare changes to the worker's assigned ownership.
5. Check tests the worker claims to have run.
6. Identify focused review findings.
7. Delegate fixes if needed.
8. Delegate final verification.
9. Commit and push only after required gates pass.

## Scope Drift

Scope drift means the patch changes more than the task required.

Warning signs:

- unrelated refactors
- renamed public concepts without need
- new dependencies
- auth/cloud/scheduling added during a local feature
- hardware required by default verifier
- tests rewritten broadly to pass
- docs updated to claim behavior that was not implemented

When scope drift appears, assign a focused fix or ask the worker to explain.
Do not accept broad changes because they look useful.

## Payload And Interface Mismatches

Frontend/backend mismatches are common in delegated work.

Check:

- route paths
- HTTP methods
- request body shape
- response field names
- redaction behavior
- default values
- selected/enabled filtering
- error handling

If frontend and backend workers use different dialects, reconcile at a narrow
backend boundary and add deterministic translation tests.

## Reviewing Shell Or Hardware Commands

Be extra strict with shell commands.

Check for:

- broad `pkill` or `pgrep -f`
- missing statement separators
- unquoted paths
- secret interpolation
- browser-provided shell text
- current-shell self-match bugs
- success reported before process health is real
- cleanup paths outside safe directories

Prefer command builders with unit tests and fake runners.

## Handling Review Findings

For one concrete bug, assign a focused fix worker.

Prompt shape:

```text
Review found one issue: [exact issue]. Fix only that issue. Add/update a
regression test. Do not broaden scope. Run [targeted test]. Do not commit.
```

Do not send the whole patch back for vague rework unless the patch is broadly
wrong. Focused fixes are easier to verify.

## Partial Or Broken Worker Output

If a worker leaves broken files:

1. Stop and close that worker.
2. Inspect current state.
3. Assign a stronger or more focused worker.
4. Tell the new worker the exact broken state.
5. Run narrow tests first.

Do not pile another broad prompt on top of broken output.

## Escalation Rules

Escalate to a stronger model or narrower prompt when:

- a worker stalls twice
- a worker returns syntax-broken code
- two subsystems need careful protocol alignment
- live hardware control has safety implications
- a small model repeatedly misses the same failure

Do not escalate by broadening the task. Escalate by improving the worker and
narrowing the assignment.

## Commit And Push Decision

Commit when:

- the diff is in scope
- required tests pass
- docs match behavior
- progress/guardrails are updated if required
- optional live checks are reported separately
- user requested or project practice expects commit/push

Do not commit when:

- verifier is red
- dirty tree includes unrelated user changes mixed with the patch
- live system is left unhealthy without user acceptance
- secrets or generated junk are staged

Before commit:

```bash
git status --short --branch
git diff --stat
```

After commit:

```bash
git status --short --branch
git rev-parse --short HEAD
```

## Final Report Shape

A good final report is concise but evidence-heavy.

Include:

- summary of what changed
- important files or subsystems
- exact verification commands
- live validation if performed
- commit hash and push status if applicable
- residual risks

Example:

```text
Done. The dashboard now stages Next Stream Settings before start, with crop off
by default and crop controls under Advanced crop.

Verification:
- `python3 -m unittest tests.test_live_display tests.test_frontend_shell`
- `scripts/verify`
- `scripts/verify-prd`
- `scripts/ralph-acceptance`

Committed and pushed:
`abc1234 Add uncropped next stream settings`
```

## Sample Review Finding

```text
Review finding: the remote command builder uses `pgrep -f "$pattern"`, but the
pattern appears in the remote shell command itself. This can make the matcher
find the shell process instead of the target service. Assign a focused fix to
match actual process cmdlines and add a regression test.
```

## Sample Integration Checklist

- [ ] Worker files match assigned ownership.
- [ ] No unrelated reversions.
- [ ] Public routes and payloads align.
- [ ] Secrets are redacted.
- [ ] Default verifier is hardware-free.
- [ ] Optional live checks are documented separately.
- [ ] Final verifier passed.
- [ ] Completed workers are closed.
- [ ] Commit contains only intended changes.
