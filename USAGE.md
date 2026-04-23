# Model Usage

This project supports both:

1. a one-shot CLI flow with `smoke-run`
2. a persistent terminal session with `interactive`

## 1. Activate The Environment

From the repo root:

```bash
source .venv/bin/activate
```

## 2. Set The Model Path

```bash
MODEL="models/Qwen3.6-35B-A3B/BF16/Qwen3.6-35B-A3B-BF16-00001-of-00002.gguf"
```

## 3. Verify ROCm And GPU Offload

Run this first:

```bash
python -m llm_gallery.cli verify-runtime --model "$MODEL"
```

This checks:

- ROCm tools are available
- the model path exists
- the `llama_cpp` backend is available
- GPU offload is supported

## 4. Import And Characterize A New Model

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

## 5. Start An Interactive Terminal Session

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

## 6. Start Interactive Mode With A Custom Context Size

```bash
python -m llm_gallery.cli interactive \
  --model "$MODEL" \
  --ctx-size 8192 \
  --max-tokens 512
```

The CLI now accepts context sizes up to the model's trained `262144` token
window, though smaller values are usually better for latency and routine
interactive work.

## 7. Run One Prompt With The One-Shot Flow

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --prompt "Explain ROCm in one sentence."
```

## 8. Run Multiple Prompts In One One-Shot Session

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --prompt "Explain ROCm in one sentence." \
  --prompt "Write one short sentence proving text generation works."
```

## 9. Change Context Size For A One-Shot Run

Example with `8192`:

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --ctx-size 8192 \
  --prompt "Summarize why GPU-only inference matters."
```

## 10. Limit Output Length

Example with `--max-tokens 16`:

```bash
python -m llm_gallery.cli smoke-run \
  --model "$MODEL" \
  --ctx-size 8192 \
  --max-tokens 16 \
  --prompt "Reply with exactly two words."
```

## 11. Run The Full Live Verifier

```bash
scripts/verify-live
```

## 12. Current Unload Behavior

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

## 13. Notes

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
