# Codex Reading Guide For `next_projects/`

This guide tells a future Codex model how to read and use this folder. It is
written directly to the model that will inherit the method.

## First Principle

Do not treat `next_projects/` as normal end-user documentation. Treat it as an
operating system for supervised project work.

Your job is not to memorize every sentence before acting. Your job is to load
the right layer of instruction for the situation:

- bootstrap a new project
- run a supervised coding session
- prompt subagents
- verify work
- diagnose live systems
- review and integrate worker output

Read deliberately, in the order below.

## Reading Order For A New Project

If this folder has just been copied into a new repository, read:

1. `README.md`
2. `bootstrap_checklist.md`
3. `project_seed/AGENTS.template.md`
4. `project_seed/TASK.template.md`
5. `project_seed/supervisor_manual.template.md`
6. `supervisory_method.md`
7. `subagent_prompt_templates.md`
8. `verification_ladder.md`
9. `review_and_integration.md`
10. `hardware_and_live_systems.md` only if the project has live services,
    devices, networking, GUI automation, external APIs, or physical hardware.

Then create or update the project's real instruction files from the templates.
Do not leave the templates as the only source of truth. They are seed material.

## Reading Order For An Existing Supervised Project

If the project already has `AGENTS.md`, `TASK.md`, progress notes, and a
supervisor manual, read those first. Then use this folder as a reference.

Recommended order:

1. Project `AGENTS.md`
2. Product source of truth, such as `prd.md`
3. Active task brief, such as `TASK.md`
4. Project supervisor manual
5. Project progress and guardrails
6. `next_projects/supervisory_method.md`
7. `next_projects/subagent_prompt_templates.md`
8. `next_projects/verification_ladder.md`
9. `next_projects/review_and_integration.md`
10. `next_projects/hardware_and_live_systems.md` if live systems are involved

Project-local instructions override portable examples. This folder teaches the
method; the project files define the current task and constraints.

## Reading Order During A Live Supervised Run

When the user explicitly asks for subagents, Ralph loops, delegated
verification, or a strict supervisory role:

1. Read `supervisory_method.md` for posture.
2. Read `subagent_prompt_templates.md` before spawning or assigning workers.
3. Read `verification_ladder.md` before deciding what "done" means.
4. Read `review_and_integration.md` before accepting worker output.
5. Read `hardware_and_live_systems.md` before touching live systems.

Do not begin by writing code. Begin by establishing role, scope, and verifier
authority.

## How To Use Each File

### `README.md`

Use this to understand what the folder is and when the method applies.

### `supervisory_method.md`

Use this to decide how to behave as the supervisor. It defines the doctrine:
what the supervisor owns, what workers own, how to poll, how to handle stalls,
and why final judgment belongs to evidence.

### `bootstrap_checklist.md`

Use this when a new repository does not yet have the structures needed for
supervised work. Follow it to create product truth, task briefs, verifier
commands, progress logs, guardrails, and done criteria.

### `subagent_prompt_templates.md`

Use this before delegating. Copy a template, fill in the blanks, and make the
worker's ownership explicit. Do not send vague prompts like "fix the project."

### `verification_ladder.md`

Use this to decide which checks to run and in what order. It also explains how
to report failures and how to separate deterministic verification from live
checks.

### `hardware_and_live_systems.md`

Use this whenever a task involves SSH, devices, streams, services, GUI state,
networking, cameras, microphones, hardware, or external APIs. It explains how
to classify failures and how to avoid leaving the system unhealthy.

### `review_and_integration.md`

Use this after workers return. It explains how to inspect diffs, catch scope
drift, identify interface mismatches, assign focused fixes, and decide whether
to commit.

### `project_seed/`

Use this to create new project-local files. Do not edit templates in place and
assume the project is configured. Copy them into the new repo, rename them, and
fill in project-specific commands and constraints.

## Decision Rules For Codex

Use these rules while reading:

- If project-local files conflict with `next_projects/`, follow project-local
  files.
- If the user explicitly requires strict supervisory mode, do not become the
  main implementor.
- If a fact can be discovered from the repo, inspect before asking.
- If the question is a user preference or tradeoff, ask before planning.
- If a worker edits files, review the diff before believing the report.
- If tests fail, do not claim done.
- If live hardware fails, classify the layer before fixing.
- If you stop a live process, restore it or report that restoration failed.
- If a worker stalls, close it before reassigning the same lane.

## Minimum Context To Carry Forward

After reading this folder, keep these ideas active:

- supervisor preserves context
- workers execute bounded tasks
- verifier output is authority
- default tests must be deterministic
- live checks are optional and separately reported
- secrets are runtime-only and redacted
- final reports must name exact commands and outcomes

## Common Mistakes

Avoid these:

- reading only the prompt templates and skipping the doctrine
- copying templates without filling in project-specific verifier commands
- treating optional hardware checks as default CI
- letting browser UI send raw shell commands
- accepting a worker's "done" without diff review
- running broad verification before fixing syntax failures
- leaving completed workers open
- hiding red checks in the final report

## If You Are Unsure

When unsure, do the conservative thing:

1. Read project-local instructions.
2. Inspect current files and git status.
3. Ask only for preferences that cannot be discovered.
4. Delegate narrowly.
5. Verify with deterministic commands.
6. Report evidence honestly.
