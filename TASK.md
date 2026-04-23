# Active Task: Qwen GGUF ROCm CLI Bootstrap

## Goal

Build the first working milestone for this repository: a CLI that can target
the existing local Qwen GGUF model, load it with `llama.cpp` on the AMD GPU,
run multiple prompts, report prompt outputs plus tokens/sec, expose per-run
context size, and unload cleanly so VRAM returns close to its baseline.

This first milestone establishes the runtime path and guardrails before the
repository expands to additional models.

## Required Deliverables

- project-local supervisor files and product/task docs
- a CLI entry point for load/test/unload workflows
- `llama.cpp` ROCm runtime bootstrap or verification
- GPU telemetry collection and reporting
- hard failure when GPU execution cannot be verified
- live load/test/unload verification against the real Qwen model

## Acceptance Criteria

1. The CLI can target the existing Qwen GGUF model with a user-supplied context
   size.
2. The runtime path rejects CPU fallback and reports an actionable failure.
3. A prompt test run executes multiple prompts and reports non-empty,
   non-garbage outputs plus token/sec.
4. GPU telemetry is reported before load, after load, during prompt execution,
   and after unload.
5. Unload returns VRAM close to the pre-load baseline and reports the result.

## Constraints

- Keep verification live.
- Do not add out-of-scope features.
- Do not require live hardware or private services unless explicitly stated.
- Preserve existing public interfaces unless this task says otherwise.
- Treat the seed Qwen model as text-only.
- Do not allow CPU inference at all.

## Required Verification

Run:

```bash
.venv/bin/python -m llm_gallery.cli plan --model models/Qwen3.6-35B-A3B/BF16/Qwen3.6-35B-A3B-BF16-00001-of-00002.gguf
scripts/verify-live
```

## Explicit Non-Goals

- spreadsheet ingestion
- web UI
- multimodal execution
- support for non-GGUF runtimes
