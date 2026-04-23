# Bootstrap Checklist For A New Supervisory Project

Use this checklist when copying the supervisory method into a new repository.
The goal is to give future Codex sessions enough structure to supervise,
delegate, verify, and recover without relying on chat memory.

## 1. Establish The Product Source Of Truth

Create one primary product document.

Recommended names:

- `prd.md`
- `PRODUCT.md`
- `docs/product.md`

It should answer:

- What is the product?
- Who uses it?
- What is v1?
- What is explicitly out of scope?
- What integrations or hardware are optional?
- What safety constraints matter?

Do not scatter product truth across many files. Workers need one place to read
first.

## 2. Create An Active Task Brief

Create `TASK.md` or equivalent.

It should include:

- active milestone name
- goal
- required deliverables
- constraints
- required verification
- acceptance criteria

Workers should be told to implement only the active task. The supervisor may
read the broader product document, but the task brief bounds the current edit.

## 3. Add Project Instructions

Create `AGENTS.md` from `project_seed/AGENTS.template.md`.

At minimum, it should define:

- read-first file order
- current project purpose
- default mode
- files or directories that should not be edited
- whether hardware or network checks are optional
- verifier commands
- done criteria
- supervisor discipline

The read-first order should be concrete. Do not say "read the relevant docs";
name the files.

## 4. Create Deterministic Verification

Create a default verifier, usually `scripts/verify`.

The default verifier should:

- run without secrets
- run without live hardware
- run without private network access
- exit nonzero on real failures
- be fast enough to run often

If the project needs live systems, create separate optional commands such as:

- `scripts/verify-hardware`
- `scripts/verify-live`
- `scripts/verify-network`

Those optional commands should skip unless an environment variable explicitly
enables them.

## 5. Add Supervisor Memory Files

Create:

- `supervisor_manual.md`
- `progress.md`
- `guardrails.md`
- `acceptance.md`

`progress.md` records what was done. `guardrails.md` records repeatable
anti-patterns. `acceptance.md` records how done is judged.

These files should be short at first. They become more useful as the project
teaches lessons.

## 6. Define Worker Contracts

Create prompt templates or copy `subagent_prompt_templates.md`.

Make sure every worker prompt answers:

- May this worker edit files?
- Which files or responsibility does it own?
- What should it not do?
- Which tests should it run?
- What final report shape is expected?

This prevents workers from overlapping and undoing each other.

## 7. Define Done Criteria

Write down what "done" means.

Good done criteria:

- required files exist
- tests pass
- default verifier passes
- milestone verifier passes
- docs match behavior
- optional hardware checks are reported separately

Bad done criteria:

- worker says it is done
- code looks plausible
- one happy path worked once
- live hardware worked but deterministic tests are red

## 8. Define What Must Not Be Implemented Yet

Every early project needs non-goals.

Examples:

- no auth in v1
- no cloud deployment
- no auto-discovery
- no destructive data migration
- no hardware requirement in default tests
- no broad refactor until scaffolding is stable

Non-goals protect the project from helpful but harmful overreach.

## 9. First Supervised Run

For the first run, the supervisor should:

1. Read `AGENTS.md`, product doc, task brief, manual, progress, and guardrails.
2. Check `git status --short --branch`.
3. Identify active milestone and scope.
4. Delegate a read-only explorer if code structure is unclear.
5. Delegate one bounded implementation task.
6. Review the diff.
7. Delegate final verification.
8. Commit only after green evidence.

## 10. Repeatable Operating Rhythm

For every later run:

- read before editing
- delegate bounded work
- review evidence
- keep default verification deterministic
- record repeatable lessons
- close workers when done
- report exact command outcomes

If the project starts to feel chaotic, narrow worker ownership and strengthen
the active task brief.
