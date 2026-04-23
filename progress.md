# Progress Log

Append newest entries at the bottom. Keep entries short, factual, and useful to
future supervisors.

## 2026-04-23 Qwen GGUF ROCm CLI Bootstrap

- Changed: bootstrapped project-local supervisor files and product/task docs for
  a ROCm-only `llama.cpp` CLI milestone.
- Verified: read `next_projects/` guidance, inspected repo state, confirmed the
  seed Qwen GGUF shards exist, confirmed ROCm tools are present, and observed
  that `rocm-smi` can see one AMD GPU in the current environment.
- Notes: `rocminfo` is blocked in the sandbox because `/dev/kfd` is not
  available there; live GPU verification may require escalated execution.

## 2026-04-23 Live Verification Shift

- Changed: moved the project rules from deterministic/fake verification to
  live ROCm-backed validation only, matching the updated user requirement.
- Verified: outside the sandbox, `rocminfo` sees the AMD GPU and
  `.venv/bin/python` with `llama_cpp` reports GPU offload support.
- Notes: the repo should use the existing ROCm-enabled `llama_cpp_python`
  binding for the first live load/test/unload milestone unless live smoke
  validation shows otherwise.

## 2026-04-23 First Live Qwen Smoke

- Changed: added a live ROCm CLI path with `plan`, `verify-runtime`, and
  `smoke-run`, plus `scripts/verify-live` as the repo verifier.
- Verified: `.venv/bin/python -m llm_gallery.cli verify-runtime` passed against
  the real Qwen BF16 GGUF model and reported `AMD Radeon Graphics` with GPU
  offload support. `scripts/verify-live` completed a real load, two prompts,
  telemetry sampling, and unload with `unload_delta_bytes=692224`. A second
  live smoke run at `--ctx-size 8192` also passed with
  `unload_delta_bytes=339968`.
- Notes: `rocm-smi` reports only `536870912` bytes of VRAM total on this APU,
  while `llama_cpp` reports `108000 MiB` total VRAM. Future supervisors should
  treat `rocm-smi` values here as the live telemetry source of record but note
  the APU reporting mismatch.

## 2026-04-23 Interactive Baseline For Foundry

- Changed: upgraded the terminal experience from a smoke-test-only flow to a
  persistent interactive ROCm session using the real Qwen GGUF model. Added
  chat-history support, direct-answer prompting through the GGUF chat template,
  higher default generation budget, `/telemetry`, `/reset`, `/max N`, and
  `/exit`. Updated `USAGE.md` to document the interactive workflow.
- Verified: live terminal sessions now answer coherently instead of emitting
  truncated reasoning scaffolds. Verified `/max 32` constrained output length,
  `/reset` cleared history without unloading, and `/exit` unloaded the model
  with `within_tolerance=True`.
- Notes: this is the current basis for Foundry. The working baseline is a
  GPU-only local terminal interface around `llama_cpp_python` with live ROCm
  verification, per-run context size, interactive prompting, and unload/VRAM
  checks.
