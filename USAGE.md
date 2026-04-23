# Model Usage

This project supports both:

1. a one-shot CLI flow with `smoke-run`
2. a persistent terminal session with `interactive`

## 1. Bootstrap A Fresh `.venv`

From the repo root, create a project-local environment that bridges the ROCm
Python base from `/opt/venv`, then installs this repo from `requirements.txt`:

```bash
./bootstrap_rocm_venv.sh
```

The bootstrap script expects the ROCm base interpreter at
`/opt/venv/bin/python3` by default. Override it with
`ROCM_BASE_PY=/path/to/python3` if your ROCm base environment lives elsewhere.

## 2. Activate The Environment

From the repo root:

```bash
source .venv/bin/activate
```

If you need to install dependencies manually instead of using the bootstrap
script, create the venv from the ROCm base interpreter, bridge the ROCm base
site-packages into it, and then install `requirements.txt`:

```bash
/opt/venv/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
OPT_SITE="$(/opt/venv/bin/python3 -c 'import site; print(site.getsitepackages()[0])')"
PYVER="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "$OPT_SITE" > ".venv/lib/python${PYVER}/site-packages/rocm_base.pth"
python -m pip install -r requirements.txt
```

`requirements.txt` installs the local repo in editable mode. The ROCm-enabled
`llama_cpp` runtime is expected to come from the bridged base environment, and
the bootstrap script verifies that GPU offload support is actually available.

## 3. Set The Model Path

```bash
MODEL="/abs/path/to/Qwen3.6-35B-A3B-BF16-00001-of-00002.gguf"
```

If you keep a shared model tree elsewhere on disk, you can also point the CLI
at that root and let it resolve the default bundled relative path:

```bash
python -m llm_gallery.cli verify-runtime --model-root /abs/path/to/models
```

## 4. Verify ROCm And GPU Offload

Run this first:

```bash
python -m llm_gallery.cli verify-runtime --model "$MODEL"
```

This checks:

- ROCm tools are available
- the model path exists
- the `llama_cpp` backend is available
- GPU offload is supported

## 5. Import And Characterize A New Model

When you add a new local model, use the import workflow to generate a profile
under `profile/` with:

- GGUF characteristics
- inferred datatype
- estimated KV-cache growth by context size
- live context stress results

Example:

```bash
python -m llm_gallery.cli import-model --model "$MODEL"
```

This writes a profile bundle such as:

```text
profile/<model-slug>/README.md
profile/<model-slug>/characteristics.json
profile/<model-slug>/context_estimate.json
profile/<model-slug>/context_stress.json
```

You can also inspect the estimate without running the full stress workflow:

```bash
python -m llm_gallery.cli estimate-context --model "$MODEL"
```

## 6. Start An Interactive Terminal Session

```bash
python -m llm_gallery.cli interactive --model "$MODEL"
```

Inside the session:

- type a prompt and press Enter
- use `/telemetry` to print current GPU stats
- use `/help` to print commands
- use `/reset` to clear chat history without unloading
- use `/max 512` to raise or lower the response token budget mid-session
- use `/exit` to unload the model and leave the session
- the session keeps chat history while it stays loaded

## 7. Start Interactive Mode With A Custom Context Size

```bash
python -m llm_gallery.cli interactive \
  --model "$MODEL" \
  --ctx-size 8192 \
  --max-tokens 512
```

The CLI now accepts context sizes up to the model's trained `262144` token
window, though smaller values are usually better for latency and routine
interactive work.

## 8. Run One Prompt With The One-Shot Flow

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --prompt "Explain ROCm in one sentence."
```

## 9. Run Multiple Prompts In One One-Shot Session

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --prompt "Explain ROCm in one sentence." \
  --prompt "Write one short sentence proving text generation works."
```

## 10. Change Context Size For A One-Shot Run

Example with `8192`:

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --ctx-size 8192 \
  --prompt "Summarize why GPU-only inference matters."
```

## 11. Limit Output Length

Example with `--max-tokens 16`:

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --ctx-size 8192 \
  --max-tokens 16 \
  --prompt "Reply with exactly two words."
```

## 12. Run The Full Live Verifier

```bash
MODEL_PATH="$MODEL" scripts/verify-live
```

The verifier also accepts `LLM_GALLERY_MODEL`, `MODEL_ROOT`, or
`LLM_GALLERY_MODEL_ROOT`.

## 13. Install The Pre-Push Regression Hook

```bash
scripts/install-git-hooks
```

After that, `git push` runs `.githooks/pre-push`, which executes the live
verifier and blocks the push on failure.

## 14. Current Unload Behavior

There is no separate standalone `unload` command yet.

In `interactive`, the model unloads when you exit the session.

In `smoke-run`, the model unloads automatically when the command finishes.

The JSON output includes:

- `before_load`
- `after_load`
- `peak_during_run`
- `after_unload`
- `unload_delta_bytes`
- `unload_within_tolerance`

## 15. Notes

- This project is GPU-only. CPU fallback is not allowed.
- The current model is treated as text-only.
- `interactive` is the current terminal-first way to talk to the model without
  reloading it for every prompt.
- The default generation budget is now larger than the original smoke-test
  setup, but you can still raise it further with `--max-tokens` for longer
  answers.
- The import workflow is now the correct place to characterize new models
  before treating them as normal Foundry-ready assets.
- For the current Qwen profile, live stress testing passed all the way up to
  `262144` context tokens.
- [CODEX_SUBMODULE.md](CODEX_SUBMODULE.md) provides the Codex-facing submodule
  bootstrap and verification flow.
