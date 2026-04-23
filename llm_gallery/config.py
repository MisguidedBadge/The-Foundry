from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_MODEL_PATH = Path(
    "models/Qwen3.6-35B-A3B/BF16/"
    "Qwen3.6-35B-A3B-BF16-00001-of-00002.gguf"
)
DEFAULT_CTX_SIZE = 4096
DEFAULT_GPU_LAYERS = -1
DEFAULT_MAX_TOKENS = 256
MIN_CTX_SIZE = 256
MAX_CTX_SIZE = 262144
DEFAULT_ROCM_TOOLS = ("rocm-smi", "rocminfo")
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant running in a local terminal session. "
    "Answer the user's question directly and clearly. "
    "Do not expose chain-of-thought or reasoning scaffolds. "
    "Do not start with phrases like 'Here's a thinking process'."
)
DEFAULT_PROMPTS = (
    "Reply with one short sentence describing what ROCm is used for.",
    "Reply with one short sentence confirming that coherent text generation is working.",
)


class ConfigError(ValueError):
    """Raised when local configuration is invalid."""


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ConfigError(f"invalid boolean value: {value!r}")


def validate_ctx_size(raw_value: object) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"ctx-size must be an integer, got {raw_value!r}") from exc
    if value < MIN_CTX_SIZE or value > MAX_CTX_SIZE:
        raise ConfigError(
            f"ctx-size must be between {MIN_CTX_SIZE} and {MAX_CTX_SIZE}, got {value}"
        )
    return value


def validate_gpu_layers(raw_value: object) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"gpu-layers must be an integer, got {raw_value!r}") from exc
    if value == 0 or value < -1:
        raise ConfigError("gpu-layers must be -1 for full offload or a positive integer")
    return value


def validate_max_tokens(raw_value: object) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"max-tokens must be an integer, got {raw_value!r}") from exc
    if value <= 0:
        raise ConfigError(f"max-tokens must be positive, got {value}")
    return value


def _resolve_candidate_path(candidate: str | Path, cwd: Path) -> Path:
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return path.resolve()


def _pick_model_from_directory(directory: Path) -> Path:
    ggufs = sorted(
        path
        for path in directory.glob("*.gguf")
        if path.is_file() and "mmproj" not in path.name.lower()
    )
    if not ggufs:
        raise ConfigError(f"no text GGUF model found under {directory}")
    split_shards = [path for path in ggufs if "00001-of-" in path.name]
    return split_shards[0] if split_shards else ggufs[0]


def resolve_model_path(model: str | None = None, cwd: Path | None = None) -> Path:
    base_dir = cwd or Path.cwd()
    candidate = model or str(DEFAULT_MODEL_PATH)
    path = _resolve_candidate_path(candidate, base_dir)
    if path.is_dir():
        path = _pick_model_from_directory(path)
    if path.suffix.lower() != ".gguf":
        raise ConfigError(f"model path must point to a .gguf file, got {path}")
    if "mmproj" in path.name.lower():
        raise ConfigError(f"multimodal projector artifacts are not supported: {path}")
    if not path.exists():
        raise ConfigError(f"model path does not exist: {path}")
    return path


@dataclass(frozen=True)
class RuntimeConfig:
    model_path: Path
    ctx_size: int
    gpu_layers: int
    cpu_fallback_allowed: bool
    rocm_tools: tuple[str, ...] = DEFAULT_ROCM_TOOLS

    @classmethod
    def from_sources(
        cls,
        *,
        model: str | None = None,
        ctx_size: int | str | None = None,
        gpu_layers: int | str | None = None,
        allow_cpu_fallback: bool | str | None = None,
        env: Mapping[str, str] | None = None,
        cwd: Path | None = None,
    ) -> "RuntimeConfig":
        environ = env if env is not None else os.environ
        base_dir = cwd or Path.cwd()

        resolved_model = resolve_model_path(model or environ.get("LLM_GALLERY_MODEL"), base_dir)
        resolved_ctx_size = validate_ctx_size(
            ctx_size if ctx_size is not None else environ.get("LLM_GALLERY_CTX_SIZE", DEFAULT_CTX_SIZE)
        )
        resolved_gpu_layers = validate_gpu_layers(
            gpu_layers if gpu_layers is not None else environ.get("LLM_GALLERY_GPU_LAYERS", DEFAULT_GPU_LAYERS)
        )
        raw_allow_cpu_fallback = (
            allow_cpu_fallback
            if allow_cpu_fallback is not None
            else environ.get("LLM_GALLERY_ALLOW_CPU_FALLBACK", False)
        )
        resolved_allow_cpu_fallback = parse_bool(raw_allow_cpu_fallback)

        return cls(
            model_path=resolved_model,
            ctx_size=resolved_ctx_size,
            gpu_layers=resolved_gpu_layers,
            cpu_fallback_allowed=resolved_allow_cpu_fallback,
        )
