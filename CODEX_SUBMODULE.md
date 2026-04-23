# Codex Submodule Entrypoint

Use this repo as an owned submodule, not as the place where parent-project
logic or model assets live.

## Working stance

- Run commands from this submodule root.
- Keep GGUF models outside the submodule checkout.
- Never rely on CPU fallback. GPU-only ROCm/HIP execution is required.
- Treat the current Qwen artifact as text-only. Ignore any `mmproj` file.

## Bootstrap

From the parent repo:

```bash
git submodule update --init --recursive
cd path/to/this/submodule
./bootstrap_rocm_venv.sh
```

Use the project-local interpreter after bootstrap:

```bash
.venv/bin/python -m llm_gallery.cli --help
```

## Point to a model outside the submodule

Pass an absolute model path on the command line:

```bash
.venv/bin/python -m llm_gallery.cli verify-runtime \
  --model /abs/path/to/model.gguf
```

Or export it once for repeated commands:

```bash
export LLM_GALLERY_MODEL=/abs/path/to/model.gguf
```

If you pass a directory instead of a file, the CLI will pick the first
non-`mmproj` `.gguf` it finds.

## Verification flow

Start with a lightweight config check:

```bash
.venv/bin/python -m llm_gallery.cli plan --model "${LLM_GALLERY_MODEL}"
```

Confirm ROCm runtime availability and GPU offload:

```bash
.venv/bin/python -m llm_gallery.cli verify-runtime \
  --model "${LLM_GALLERY_MODEL}"
```

Run the live verifier with the external model path wired into the script:

```bash
MODEL_PATH="${LLM_GALLERY_MODEL}" scripts/verify-live
```

Optional verifier knobs:

```bash
MODEL_PATH="${LLM_GALLERY_MODEL}" CTX_SIZE=8192 MAX_TOKENS=64 scripts/verify-live
```

`scripts/verify-live` runs `verify-runtime` and then a live `smoke-run`. A task
is not done unless that live verifier is green.
