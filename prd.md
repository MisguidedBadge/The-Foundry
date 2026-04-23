# Product Requirements

## Purpose

This project provides a local CLI for exploring and testing large language
models stored on disk. The operator can load a model, run multiple prompts
against it, inspect GPU usage, change context size per run, and unload the
model so VRAM is released.

## Initial Scope

Version 1 is intentionally narrow:

- CLI only
- local models only
- `llama.cpp` runtime only
- GGUF model format only
- ROCm/HIP GPU execution only
- no CPU inference fallback
- first supported model path is the existing local Qwen GGUF model on disk

## Primary User

The primary user is an operator validating local LLM runtime behavior on an AMD
GPU system. The user needs fast confidence that a model can load, answer
non-garbage prompts, report token throughput, and release VRAM when unloaded.

## Core Capabilities

- discover or register local GGUF models manually
- load a selected model with an explicit per-run context size
- reject runs that do not use the local AMD GPU through ROCm/HIP
- run multiple prompts in sequence against the loaded model
- report prompt outputs, token throughput, and GPU telemetry
- unload the model and confirm VRAM returns close to the pre-load baseline

## Required Telemetry

For v1, report:

- HIP-visible device name
- VRAM used/free
- GPU utilization

Sampling points:

- before load
- after load
- during prompt execution
- after unload

## Output Quality Standard

V1 prompt validation is a smoke test, not a benchmark. Output must be:

- non-empty
- not obvious garbage
- not degenerate repetition

## Hard Constraints

- Never allow CPU inference fallback.
- Fail fast if the runtime cannot confirm GPU use.
- Treat the current Qwen model as text-only and ignore vision paths.
- Keep context size editable per run.
- Use ROCm/HIP-specific tooling where needed.
- Use live validation against the real runtime and model; do not substitute
  fake or virtual tests.

## Non-Goals

- spreadsheet ingestion or automated model catalog sync
- web UI
- multimodal support
- CPU inference mode
- support for non-GGUF formats in v1
- broad model-management automation
