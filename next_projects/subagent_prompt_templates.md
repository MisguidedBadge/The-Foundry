# Subagent Prompt Templates

These templates are meant to be copied into future Codex sessions. Replace the
bracketed fields before use. Keep prompts specific. A vague worker prompt is the
fastest way to create drift.

## Universal Worker Rules

Include these rules in most worker prompts:

```text
You are not alone in the codebase. Do not revert edits made by others. Work
with existing changes unless they make the task impossible. Do not commit or
push. Report changed files, commands run, and residual risks.
```

For read-only workers, add:

```text
Do not edit files. Do not run mutating commands. Collect evidence and report.
```

For hardware workers, add:

```text
Do not leave the live system worse than you found it. If you stop a service,
restart it and verify health before finishing unless explicitly told not to.
```

## Read-Only Explorer

```text
You are the read-only explorer delegate. Do not edit files, commit, push, or
run mutating commands.

Workspace: [absolute repo path]

Goal: [specific question to answer]

Read these first:
- [project instructions]
- [active task]
- [specific files likely relevant]

Return:
- concise answer
- exact files/functions involved
- risks or ambiguity
- recommended implementation direction

Do not implement the fix.
```

Use this when the supervisor needs facts before planning or assigning work.

## Implementation Worker

```text
You are the implementation delegate. You own the file edits for this bounded
task.

Workspace: [absolute repo path]

User goal: [goal]
Active scope: [milestone or task]

You are not alone in the codebase. Do not revert edits made by others. Keep the
change scoped to:
- [owned file or subsystem]

Non-goals:
- [thing not to implement]
- [thing not to refactor]

Implementation requirements:
- [requirement 1]
- [requirement 2]
- [requirement 3]

Tests to run:
- [targeted command]
- [optional command]

Final report:
- files changed
- behavior changed
- tests run with exact results
- caveats or residual risks

Do not commit or push.
```

Use this for bounded changes with clear ownership.

## Verification Worker

```text
You are the verification delegate. Do not edit files, commit, push, or touch
live systems unless explicitly instructed.

Workspace: [absolute repo path]

Verify the current patch for: [feature/fix].

Run:
- [targeted tests]
- [default verifier]
- [milestone verifier]
- [acceptance command]

Also perform this static review:
- [checklist item]
- [checklist item]

Report:
- each command
- pass/fail
- exact key output
- likely cause for any failure
- whether failures appear related, pre-existing, or environmental
- residual risks
```

Use this after implementation and focused fixes.

## Live Diagnostic Worker

```text
You are the live diagnostic delegate. Do not edit repo files, commit, or push.
Use only safe diagnostics unless explicitly authorized.

Workspace: [absolute repo path]

Live system goal:
[example: determine why device X is connected but API health fails]

Known expected config:
- host: [host/IP]
- user: [user]
- key: [key path]
- service/port: [port]

Allowed checks:
- [curl health endpoint]
- [SSH read-only commands]
- [process listing]
- [logs under specific safe paths]

Do not:
- print secrets
- inspect broad secret-bearing directories
- kill services unless explicitly asked
- leave final state unhealthy

Return:
- exact evidence
- likely cause
- smallest fix or workaround
- whether final live state is healthy
```

Use this for hardware, services, network, GUI automation, or other live paths.

## Focused Fix Worker

```text
You are the focused fix delegate. A review found one specific issue. Fix only
that issue.

Workspace: [absolute repo path]

Known problem:
[exact review finding]

Required fix:
[precise behavior]

Do not:
- broaden scope
- refactor unrelated code
- change public behavior beyond the fix
- commit or push

Run:
- [small targeted test]

Report:
- changed files
- exact test result
- any remaining risk
```

Use this when review finds a concrete bug in a worker patch.

## Stalled Worker Replacement

```text
You are replacing a stalled worker. Do not assume the previous worker completed
correctly.

Workspace: [absolute repo path]

Known state:
- [files changed or suspected]
- [known failure]
- [commands that failed]

Task:
[repair or complete a narrow lane]

Rules:
- inspect current files before editing
- preserve unrelated changes
- keep ownership to [files/subsystem]
- run targeted tests before broad tests
- do not commit or push

Report:
- what was broken
- what you changed
- tests run
- whether the lane is now ready for final verification
```

Use this when a worker is silent, broken, or out of scope.

## Process-Note Or Documentation Worker

```text
You are the docs/process-note delegate. Keep this to documentation only.

Workspace: [absolute repo path]

Task:
[documentation update]

Sources to preserve:
- [source doc]
- [source doc]

Requirements:
- [portable/generic/project-specific]
- [verbosity level]
- [files to create or update]

Do not:
- modify product code
- change verifier behavior
- commit or push

Run:
- [docs or repo verifier if appropriate]

Report:
- changed files
- commands run
- whether content is portable or project-specific
```

Use this for manuals, progress notes, templates, and checklists.

## Final Verifier

```text
You are the final verification delegate. Do not edit files, commit, push, or
touch live systems.

Workspace: [absolute repo path]

Run the final gate set:
- [targeted tests]
- [default verifier]
- [milestone verifier]
- [acceptance command]

Static review checklist:
- [must-have behavior]
- [must-not-have behavior]
- [docs updated]

Report exact pass/fail evidence. If anything fails, include the failing command
and the important output. Do not fix failures.
```

Use this immediately before integration.

## Bad Prompt Examples

Avoid prompts like these:

```text
Look around and fix whatever seems wrong.
```

Why it is bad: no scope, no ownership, no verification target.

```text
Implement the frontend and backend changes.
```

Why it is bad: too broad; likely file ownership overlap.

```text
Run tests and fix them.
```

Why it is bad: mixes verification and implementation without boundaries.

```text
SSH into the server and make it work.
```

Why it is bad: unsafe, no final-state requirement, no secret boundaries.

## Good Prompt Pattern

A good prompt is boring, explicit, and bounded:

```text
You are the focused fix delegate. Fix only the malformed shell command in
backend/process_control.py. The generated start and kill scripts must include a
statement separator after the matcher loop. Add a regression test proving the
bad strings are absent. Run `python3 -m unittest tests.test_process_control`.
Do not commit or push.
```

The worker knows what to do, where to do it, what not to do, and how to prove it.
