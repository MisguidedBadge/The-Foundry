# Portable Supervisory Method Kit

This folder is a portable bootstrap kit for the supervisory/subagent method
used in this repository. Copy `next_projects/` into a new project when you want
a future Codex session to operate as a context-preserving supervisor instead of
a single agent trying to hold the entire project in one thread.

The goal is simple: make complex work repeatable. A supervisor keeps product
intent, scope, and final judgment in one place while short-lived workers perform
bounded exploration, implementation, verification, and live diagnostics.

## What This Method Is

The supervisory method has one lead agent and many small worker lanes.

The supervisor owns:

- product intent and active scope
- task decomposition
- worker prompts and ownership boundaries
- review of worker diffs and evidence
- final verification interpretation
- user-facing summaries and decisions

Workers own:

- read-only discovery
- bounded implementation slices
- focused fixes
- targeted verification
- optional live or hardware diagnostics

The supervisor should not become the primary implementor once the user has
asked for subagents, Ralph loops, delegated verification, or a strict
supervisory mode. The supervisor may still perform small integration steps,
read files, review diffs, commit, or push when appropriate, but its default job
is orchestration and judgment.

## When To Use It

Use this method when any of these are true:

- The task is multi-step and easy to lose context on.
- Multiple subsystems are involved, such as frontend, backend, docs, and tests.
- A live system or hardware device must be diagnosed separately from default
  verification.
- You need repeated refinement, not a one-shot patch.
- The user explicitly asks for subagents, Ralph loops, delegated verification,
  or a supervisory role.
- The project needs a repeatable milestone loop with evidence-heavy reports.

Do not force this method onto tiny tasks. A one-line typo fix does not need a
supervisor, workers, and final verifier. The method is strongest when context
preservation matters more than raw speed.

## How To Bootstrap A New Project

1. Copy this entire folder into the new repository as `next_projects/`.
2. Copy the files from `next_projects/project_seed/` into the repository root or
   project control folder.
3. Rename the copied templates by removing `.template` from the filenames.
4. Fill in the product source of truth, active task, verifier commands, and
   project-specific constraints.
5. Add a deterministic default verifier before doing live hardware work.
6. Instruct future Codex sessions to read the copied `AGENTS.md` and supervisor
   manual before changing code.

Minimum recommended files in a new project:

- `AGENTS.md`
- `TASK.md`
- `supervisor_manual.md`
- `progress.md`
- `guardrails.md`
- `acceptance.md`
- one verifier command, such as `scripts/verify`

## The Supervisor Loop

The loop is:

1. Read project instructions and active task.
2. Inspect the dirty tree.
3. Identify the critical path and scope boundary.
4. Delegate bounded read-only discovery if facts are missing.
5. Delegate implementation with clear file ownership.
6. Review the worker diff and claims.
7. Delegate focused fixes for review findings.
8. Delegate final verification to a separate worker.
9. Integrate only after evidence is green.
10. Commit, push, and report exact verification outcomes when requested.

The final decision should be grounded in verifier output, not worker confidence.

## How This Differs From A Single-Agent Session

A single-agent session tends to mix discovery, implementation, testing, and
judgment in one thread. That can work for small changes, but it becomes fragile
when the problem is long-running or hardware-involved.

The supervisory method separates concerns:

- Explorers answer questions without mutating files.
- Workers change owned areas without also judging final readiness.
- Verification workers run checks without writing code.
- The supervisor integrates evidence and protects scope.

That separation makes it easier to recover from partial work. If one worker
stalls or returns a broken patch, the supervisor closes that lane and assigns a
focused repair without losing the rest of the session.

## Contents

- `codex_reading_guide.md`: reading order and interpretation instructions for
  future Codex models.
- `supervisory_method.md`: long-form doctrine and operating rules.
- `bootstrap_checklist.md`: step-by-step setup for a new project.
- `subagent_prompt_templates.md`: copy-ready worker prompts.
- `verification_ladder.md`: testing and evidence strategy.
- `hardware_and_live_systems.md`: optional live system and hardware discipline.
- `review_and_integration.md`: diff review, fixes, final reports, and commits.
- `project_seed/`: generic starter files for new repositories.

## Golden Rule

The supervisor must preserve context and truth. Delegate the work, review the
evidence, and never claim success just because a worker sounded confident.

## Note To Future Codex

Start with `codex_reading_guide.md` if you are the model inheriting this folder.
It tells you what to read first, when to use each document, and how to translate
the portable kit into project-local operating rules.
