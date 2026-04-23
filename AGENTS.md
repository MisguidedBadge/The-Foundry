# AGENTS.md

## Repository Purpose

This repository builds a local CLI for loading, testing, and unloading GGUF
LLM models with `llama.cpp` on AMD ROCm/HIP GPUs only. The first milestone is a
working end-to-end path for the existing Qwen GGUF model in `models/`, with
per-run context size, prompt smoke tests, token/sec reporting, GPU telemetry,
and VRAM release on unload.

## Read-First Order

Before making changes, read these files when they exist:

1. `README.md`
2. `prd.md`
3. `TASK.md`
4. `supervisor_manual.md`
5. `guardrails.md`
6. `progress.md`

## Core Working Rules

- Implement only the active task described in `TASK.md`.
- Prefer the smallest change set that satisfies the task.
- Do not claim success unless required verification passes.
- When behavior changes, update the live verification path.
- Treat existing uncommitted changes as user or prior-agent work.
- Do not revert unrelated changes unless explicitly requested.
- Do not edit secrets, credentials, or private key material.
- Never allow CPU inference fallback.
- Fail fast if GPU execution through ROCm/HIP cannot be verified.
- Treat the current Qwen model as text-only even though an `mmproj` artifact is
  present.

## Default Verification

The default verifier is live:

```bash
scripts/verify-live
```

Verification in this repository is expected to use the real ROCm-backed
runtime, the real local model path, and the real GPU telemetry path. Do not add
stub, fake, or virtual tests in place of live validation.

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
- live verifier is green
- GPU-only execution is enforced with no CPU fallback path
