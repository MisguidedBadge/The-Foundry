# Supervisory Method Doctrine

This document explains the supervisory/subagent method in enough detail for a
future Codex model to reproduce it in a new project. It is intentionally more
explicit than normal project documentation because it is meant to transfer an
operating method from one model session to another.

## Core Idea

One supervisor coordinates many bounded workers.

The supervisor is responsible for continuity. It remembers the active task,
protects the scope boundary, watches for drift, reviews evidence, and decides
whether the work is truly done.

Workers are responsible for bounded execution. They can explore, edit, verify,
or diagnose, but each worker should have one clear job and one clear final
report.

The method works because it reduces context overload. The supervisor does not
need to personally perform every file edit or every test. Instead, it keeps a
high-quality map of what is happening and ensures each subtask has evidence.

## Supervisor Responsibilities

The supervisor owns the following decisions:

- What is the user's real goal?
- What is in scope for the current milestone?
- What must not be implemented yet?
- Which facts can be discovered locally?
- Which work can be delegated safely?
- Which files or responsibilities does each worker own?
- Which worker claims require independent verification?
- Which failures are blockers and which are residual risks?
- Whether a patch is safe to commit and push.

The supervisor should speak to the user often enough that the user can see the
shape of the work. Updates should be short, concrete, and tied to the current
state: what was learned, what was delegated, what is being reviewed, or what is
blocked.

## Worker Roles

Use worker roles deliberately.

### Explorer

An explorer is read-only. It answers a specific question about the repo,
environment, product intent, or live system. It should not edit files.

Good explorer tasks:

- "Find where the frontend builds the live-display payload."
- "Compare the current docs with the active milestone."
- "Check whether the Pi is reachable and whether the agent listens on port
  8080."
- "Inspect test failures and identify the smallest likely fix."

Bad explorer tasks:

- "Figure everything out."
- "Fix the UI if you see anything wrong."
- "Refactor the backend."

### Implementation Worker

An implementation worker owns a bounded patch. It should have a clear file set
or responsibility area. It should know that other agents may be editing the repo
and that it must not revert unrelated changes.

Good implementation tasks:

- "Update only the dashboard component and shell tests."
- "Add a fakeable SSH runner and deterministic tests."
- "Fix the command builder separator bug and add a regression test."

Bad implementation tasks:

- "Improve the project."
- "Rewrite the app."
- "Make whatever changes are necessary."

### Verification Worker

A verification worker does not edit files. It runs commands, captures exact
output, and performs static review against a checklist. It is most useful after
implementation and focused fixes.

The verification worker should report:

- command run
- pass/fail
- key output, such as test counts or error lines
- whether failures appear related, pre-existing, or environmental
- residual risks

### Live Diagnostic Worker

A live diagnostic worker investigates a real system, hardware device, network,
or process. It should be read-only unless the task explicitly requires a
controlled action such as starting a service and checking health.

Live diagnostics must preserve final state. If a worker kills a service to test
the kill path, it must restart the service and verify health afterward.

## The "Do Not Become The Implementor" Rule

When the user asks for supervisory mode, the supervisor must not quietly become
the main coder. This rule exists because the value of supervision is context
preservation. If the supervisor performs every edit and every test, there is no
separation of concerns.

Allowed supervisor work:

- reading files
- reviewing diffs
- closing workers
- committing and pushing reviewed work
- making tiny integration edits when delegation would add overhead
- writing final summaries

Preferred delegated work:

- broad implementation
- live diagnostics
- final verification
- focused fixes after review
- docs generation when the docs are large

If the supervisor must make a local edit, it should say why and keep the edit
small. The default should remain delegation.

## Task Decomposition

Before delegation, the supervisor should divide the problem into lanes:

- discovery lane: facts that are missing
- implementation lane: owned patch areas
- verification lane: commands and evidence
- live validation lane: optional hardware or environment proof
- integration lane: review, commit, push, final answer

Avoid assigning two workers to edit the same file at the same time. If overlap
is unavoidable, split the work by responsibility and make one worker wait for
the other to finish.

## Worker Prompt Anatomy

A strong worker prompt includes:

- role: explorer, worker, verifier, or live diagnostic
- repository path
- current user goal
- active milestone or task boundary
- file ownership or read-only instruction
- explicit non-goals
- warning not to revert unrelated changes
- exact tests or checks to run
- final report requirements

Include enough context for the worker to succeed, but do not overload it with
the entire conversation. The worker should receive a crisp job, not a cloud of
ambiguous history.

## Polling And Stalls

Supervisors should poll workers periodically. Polling is not impatience; it is
visibility.

Recommended cadence:

- first status check after roughly 30 seconds for active work
- longer wait windows for full-model implementation or broad verification
- ask for a checkpoint if a worker exceeds one or two expected windows
- close and replace a worker if it ignores a checkpoint or drifts off scope

A long-running worker is not automatically failed. It may be doing useful work.
Failure signs are silence after a status request, repeated tool errors, broken
partial output, or ownership drift.

## Handling Partial Worker Output

If a worker returns broken or incomplete work:

1. Stop and close the worker.
2. Inspect the changed files.
3. Do not run the full verifier until syntax is repaired.
4. Delegate a focused fix with the known failure mode.
5. Run targeted tests before broad tests.

Do not shame the worker or discard the whole method. Partial output is a signal
to narrow scope, improve prompts, or escalate model strength.

## Model Selection

Use smaller or faster models for:

- read-only repo mapping
- simple docs updates
- targeted verification
- isolated tests
- small focused fixes

Use stronger models for:

- cross-cutting implementation
- repair after a stalled worker
- protocol design
- hardware-control safety
- frontend/backend integration
- anything that already failed once

The supervisor may start with a smaller worker and escalate only if there is
evidence of difficulty.

## Evidence Hierarchy

The evidence hierarchy is:

1. deterministic verifier output
2. targeted test output
3. static diff review
4. live diagnostic evidence
5. worker narrative

Worker narrative is useful, but it is not proof. A worker saying "done" does
not override a failing verifier.

## Final Judgment

The supervisor's final answer should include:

- what changed
- what was verified
- exact commands that passed or failed
- live checks, if any
- residual risks or blocked checks
- commit and push status, if applicable

It should not hide failures. If a verifier is red, the task is not fully done.
