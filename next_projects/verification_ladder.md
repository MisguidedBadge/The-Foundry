# Verification Ladder

The verification ladder is the method for deciding whether work is actually
done. It starts narrow, becomes broader, and keeps live hardware separate from
default project verification.

## Core Rule

Verifier output beats worker confidence.

A worker saying "it should work" is useful context. A passing verifier is
evidence. A failing verifier is a blocker unless the user explicitly accepts the
risk.

## Recommended Ladder

1. Syntax or import checks for newly touched modules.
2. Targeted tests for the changed surface.
3. Frontend or backend build checks, if relevant.
4. Default verifier, such as `scripts/verify`.
5. Milestone or PRD verifier, such as `scripts/verify-prd`.
6. Acceptance command, such as `scripts/ralph-acceptance`.
7. Optional live hardware or network checks.

The exact commands vary by project, but the shape should remain the same:
narrow proof first, broad proof second, live proof last.

## Narrow Tests

Run narrow tests immediately after a worker changes code.

Examples:

- a unit test module for the touched backend file
- a component shell test for a frontend label change
- a command-builder test after shell quoting changes
- a schema test after payload changes

Narrow tests give fast feedback and help identify whether a focused fix worked.

## Broad Verifier

The default verifier should be deterministic and hardware-free.

It should not require:

- SSH
- real devices
- private network access
- GUI permissions
- cloud credentials
- manual operator input
- real payment or production systems

If any of those are needed, put them behind an optional verifier.

## Milestone Verifier

A milestone verifier checks that the current task aligns with the product plan.
It is different from a unit test. It may check required files, expected docs,
scaffold shape, or milestone-specific tokens.

Use it to prevent code that passes tests but violates the project plan.

## Acceptance Checks

Acceptance checks should answer: "Does the loop still behave correctly?"

Examples:

- verifier authority is preserved
- safe no-diff stops still work
- artifacts are auditable
- docs match commands

Acceptance checks are especially useful in projects with autonomous coding
loops, supervisory modes, or PRD-driven milestones.

## Optional Live Checks

Live checks are valuable but must be labeled correctly.

Examples:

- SSH to a device
- stream video to hardware
- probe a local camera
- bind a multicast port
- start or kill a remote service

Passing a live check does not replace deterministic tests. Failing a live check
does not necessarily mean the code is wrong; it may indicate environment,
network, permissions, or hardware state.

Report live checks separately:

```text
Default verification: passed.
Optional live check: failed because device was offline.
```

## Reporting Failures

A verifier report should include:

- exact command
- exit status if known
- important stdout/stderr
- likely category
- whether it blocks completion

Failure categories:

- related code regression
- test expectation mismatch
- environment limitation
- missing dependency
- permission or sandbox issue
- live hardware unavailable
- pre-existing unrelated failure

Do not summarize a failure as "tests failed" without the command and key lines.

## Green Tests Versus Readiness

Green deterministic tests mean the code satisfies the testable contract.

They do not automatically prove:

- hardware is online
- network routes are correct
- GUI permissions are granted
- credentials are valid
- production deployment is safe

For live systems, pair green default tests with optional live validation when
the user asks for real-world confidence.

## Handling Red Tests

If a narrow test fails:

1. Assign a focused fix worker.
2. Run the narrow test again.
3. Do not run the full verifier until the narrow failure is repaired.

If the broad verifier fails:

1. Identify whether the failure is related to the patch.
2. Ask a verification or explorer worker to classify the failure.
3. Fix related failures.
4. Report unrelated or environmental failures honestly.

If optional hardware fails:

1. Check network reachability.
2. Check auth.
3. Check service/process state.
4. Check package/runtime availability.
5. Check logs.
6. Restore final healthy state if possible.

## Sample Verifier Report

```text
Verification complete. I did not edit files.

- `python3 -m unittest tests.test_backend_api`
  - Pass
  - `Ran 12 tests in 0.018s`
  - `OK`

- `scripts/verify`
  - Fail
  - Key output: `frontend shell missing token: Live Status`
  - Category: related test expectation mismatch
  - Blocker: yes

Recommended next action: focused frontend/check-scaffold fix.
```

## Final Verification Standard

Before a supervisor claims completion, the relevant required gates must pass or
the final answer must clearly say which gates are red and why.
