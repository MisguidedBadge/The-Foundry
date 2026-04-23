from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .runtime import RuntimeVerificationError, run_live_smoke


DEFAULT_STRESS_CTX_SIZES = (4096, 8192, 16384, 32768, 65536, 131072, 262144)
DEFAULT_STRESS_PROMPT = "In one sentence, confirm that context stress testing is running."
DEFAULT_STRESS_MAX_TOKENS = 24


@dataclass(frozen=True)
class ModelCharacteristics:
    model_name: str
    basename: str | None
    architecture: str | None
    size_label: str | None
    repo_url: str | None
    license_name: str | None
    quantized_by: str | None
    file_type_code: int | None
    inferred_datatype: str
    context_length: int | None
    block_count: int | None
    embedding_length: int | None
    attention_head_count: int | None
    attention_head_count_kv: int | None
    attention_key_length: int | None
    attention_value_length: int | None
    expert_count: int | None
    expert_used_count: int | None
    model_files: tuple[str, ...]
    total_model_bytes: int


@dataclass(frozen=True)
class ContextEstimate:
    kv_bytes_per_token: int
    kv_mib_per_1k_tokens: float
    ctx_sizes: tuple[int, ...]
    estimated_kv_bytes_by_ctx: dict[str, int]
    estimated_kv_gib_by_ctx: dict[str, float]
    recommended_interactive_ctx: int
    recommended_long_ctx: int
    recommended_tested_ceiling_ctx: int


@dataclass(frozen=True)
class ContextStressResult:
    ctx_size: int
    ok: bool
    error: str | None
    load_vram_delta_bytes: int | None
    peak_vram_used_bytes: int | None
    peak_gpu_use_percent: int | None
    unload_delta_bytes: int | None
    unload_within_tolerance: bool | None
    completion_tokens: int | None
    tokens_per_second: float | None
    output_preview: str | None


@dataclass(frozen=True)
class ImportedModelProfile:
    slug: str
    model_path: str
    characteristics: ModelCharacteristics
    estimate: ContextEstimate
    stress_results: tuple[ContextStressResult, ...]
    profile_dir: str


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "model"


def _collect_model_files(model_path: Path) -> tuple[Path, ...]:
    name = model_path.name
    shard_match = re.match(r"^(?P<prefix>.+)-\d{5}-of-\d{5}\.gguf$", name)
    if not shard_match:
        return (model_path,)
    prefix = shard_match.group("prefix")
    pattern = f"{prefix}-*.gguf"
    files = sorted(
        candidate
        for candidate in model_path.parent.glob(pattern)
        if candidate.is_file() and "mmproj" not in candidate.name.lower()
    )
    return tuple(files) if files else (model_path,)


def _infer_datatype(model_path: Path, metadata: dict[str, Any]) -> str:
    upper_name = model_path.name.upper()
    if "BF16" in upper_name:
        return "BF16"
    if "F16" in upper_name or "FP16" in upper_name:
        return "FP16"
    if "Q8" in upper_name:
        return "Q8"
    if "Q6" in upper_name:
        return "Q6"
    if "Q5" in upper_name:
        return "Q5"
    if "Q4" in upper_name:
        return "Q4"
    file_type = metadata.get("general.file_type")
    if file_type == 32:
        return "BF16 (inferred)"
    return f"unknown (file_type={file_type})"


def _load_live_metadata(config: RuntimeConfig) -> dict[str, Any]:
    from .runtime import _load_llama_cpp  # local import to avoid broad surface

    llama_cpp = _load_llama_cpp()
    llm = llama_cpp.Llama(
        model_path=str(config.model_path),
        n_gpu_layers=config.gpu_layers,
        n_ctx=config.ctx_size,
        use_mmap=False,
        offload_kqv=True,
        verbose=False,
    )
    try:
        return dict(llm.metadata)
    finally:
        llm.close()
        del llm
        time.sleep(1.0)


def inspect_model_characteristics(config: RuntimeConfig) -> ModelCharacteristics:
    metadata = _load_live_metadata(config)
    architecture = metadata.get("general.architecture")
    arch_prefix = architecture if isinstance(architecture, str) else ""
    model_files = _collect_model_files(config.model_path)
    total_model_bytes = sum(path.stat().st_size for path in model_files)

    def meta_int(key: str) -> int | None:
        value = metadata.get(key)
        return int(value) if value is not None else None

    return ModelCharacteristics(
        model_name=str(metadata.get("general.name") or config.model_path.stem),
        basename=metadata.get("general.basename"),
        architecture=architecture,
        size_label=metadata.get("general.size_label"),
        repo_url=metadata.get("general.base_model.0.repo_url") or metadata.get("general.repo_url"),
        license_name=metadata.get("general.license"),
        quantized_by=metadata.get("general.quantized_by"),
        file_type_code=meta_int("general.file_type"),
        inferred_datatype=_infer_datatype(config.model_path, metadata),
        context_length=meta_int(f"{arch_prefix}.context_length"),
        block_count=meta_int(f"{arch_prefix}.block_count"),
        embedding_length=meta_int(f"{arch_prefix}.embedding_length"),
        attention_head_count=meta_int(f"{arch_prefix}.attention.head_count"),
        attention_head_count_kv=meta_int(f"{arch_prefix}.attention.head_count_kv"),
        attention_key_length=meta_int(f"{arch_prefix}.attention.key_length"),
        attention_value_length=meta_int(f"{arch_prefix}.attention.value_length"),
        expert_count=meta_int(f"{arch_prefix}.expert_count"),
        expert_used_count=meta_int(f"{arch_prefix}.expert_used_count"),
        model_files=tuple(str(path) for path in model_files),
        total_model_bytes=total_model_bytes,
    )


def estimate_context(
    characteristics: ModelCharacteristics,
    *,
    ctx_sizes: tuple[int, ...] = DEFAULT_STRESS_CTX_SIZES,
    tested_success_ctxs: tuple[int, ...] = (),
) -> ContextEstimate:
    if (
        characteristics.block_count is None
        or characteristics.attention_head_count_kv is None
        or characteristics.attention_key_length is None
        or characteristics.attention_value_length is None
    ):
        raise RuntimeVerificationError("model metadata is missing KV sizing fields")

    kv_bytes_per_token = (
        characteristics.block_count
        * characteristics.attention_head_count_kv
        * (characteristics.attention_key_length + characteristics.attention_value_length)
        * 2
    )
    estimated_kv_bytes_by_ctx = {
        str(ctx_size): kv_bytes_per_token * ctx_size for ctx_size in ctx_sizes
    }
    estimated_kv_gib_by_ctx = {
        key: round(value / (1024 ** 3), 3) for key, value in estimated_kv_bytes_by_ctx.items()
    }

    successful = tuple(sorted(tested_success_ctxs))
    recommended_interactive_ctx = 16384
    recommended_long_ctx = 32768
    recommended_tested_ceiling_ctx = successful[-1] if successful else max(ctx_sizes)

    if successful:
        recommended_interactive_ctx = (
            16384 if 16384 in successful else max(ctx for ctx in successful if ctx <= 16384)
        )
        long_candidates = [ctx for ctx in successful if ctx <= 32768]
        recommended_long_ctx = (
            32768 if 32768 in successful else (long_candidates[-1] if long_candidates else successful[-1])
        )
    else:
        recommended_interactive_ctx = min(16384, max(ctx_sizes))
        recommended_long_ctx = min(32768, max(ctx_sizes))

    return ContextEstimate(
        kv_bytes_per_token=kv_bytes_per_token,
        kv_mib_per_1k_tokens=round((kv_bytes_per_token * 1024) / (1024 ** 2), 3),
        ctx_sizes=ctx_sizes,
        estimated_kv_bytes_by_ctx=estimated_kv_bytes_by_ctx,
        estimated_kv_gib_by_ctx=estimated_kv_gib_by_ctx,
        recommended_interactive_ctx=recommended_interactive_ctx,
        recommended_long_ctx=recommended_long_ctx,
        recommended_tested_ceiling_ctx=recommended_tested_ceiling_ctx,
    )


def stress_test_contexts(
    config: RuntimeConfig,
    *,
    ctx_sizes: tuple[int, ...],
    prompt: str = DEFAULT_STRESS_PROMPT,
    max_tokens: int = DEFAULT_STRESS_MAX_TOKENS,
) -> tuple[ContextStressResult, ...]:
    results: list[ContextStressResult] = []
    for ctx_size in ctx_sizes:
        run_config = RuntimeConfig(
            model_path=config.model_path,
            ctx_size=ctx_size,
            gpu_layers=config.gpu_layers,
            cpu_fallback_allowed=config.cpu_fallback_allowed,
            rocm_tools=config.rocm_tools,
        )
        try:
            smoke = run_live_smoke(run_config, prompts=(prompt,), max_tokens=max_tokens)
            prompt_result = smoke.prompts[0]
            results.append(
                ContextStressResult(
                    ctx_size=ctx_size,
                    ok=True,
                    error=None,
                    load_vram_delta_bytes=smoke.after_load.vram_used_bytes - smoke.before_load.vram_used_bytes,
                    peak_vram_used_bytes=smoke.peak_during_run.vram_used_bytes,
                    peak_gpu_use_percent=smoke.peak_during_run.gpu_use_percent,
                    unload_delta_bytes=smoke.unload_delta_bytes,
                    unload_within_tolerance=smoke.unload_within_tolerance,
                    completion_tokens=prompt_result.completion_tokens,
                    tokens_per_second=prompt_result.tokens_per_second,
                    output_preview=prompt_result.output[:240],
                )
            )
        except Exception as exc:
            results.append(
                ContextStressResult(
                    ctx_size=ctx_size,
                    ok=False,
                    error=str(exc),
                    load_vram_delta_bytes=None,
                    peak_vram_used_bytes=None,
                    peak_gpu_use_percent=None,
                    unload_delta_bytes=None,
                    unload_within_tolerance=None,
                    completion_tokens=None,
                    tokens_per_second=None,
                    output_preview=None,
                )
            )
            break
    return tuple(results)


def write_model_profile(profile: ImportedModelProfile) -> tuple[Path, Path, Path]:
    profile_dir = Path(profile.profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    characteristics_path = profile_dir / "characteristics.json"
    estimate_path = profile_dir / "context_estimate.json"
    stress_path = profile_dir / "context_stress.json"
    readme_path = profile_dir / "README.md"

    characteristics_path.write_text(
        json.dumps(asdict(profile.characteristics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    estimate_path.write_text(
        json.dumps(asdict(profile.estimate), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    stress_path.write_text(
        json.dumps([asdict(result) for result in profile.stress_results], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    successful = [result.ctx_size for result in profile.stress_results if result.ok]
    failed = [result for result in profile.stress_results if not result.ok]
    lines = [
        f"# {profile.characteristics.model_name}",
        "",
        "## Summary",
        "",
        f"- Model path: `{profile.model_path}`",
        f"- Architecture: `{profile.characteristics.architecture}`",
        f"- Datatype: `{profile.characteristics.inferred_datatype}`",
        f"- Size label: `{profile.characteristics.size_label}`",
        f"- Total local model bytes: `{profile.characteristics.total_model_bytes}`",
        f"- Max trained context: `{profile.characteristics.context_length}`",
        f"- KV bytes per token estimate: `{profile.estimate.kv_bytes_per_token}`",
        f"- Recommended interactive ctx: `{profile.estimate.recommended_interactive_ctx}`",
        f"- Recommended long ctx: `{profile.estimate.recommended_long_ctx}`",
        f"- Highest successfully stress-tested ctx: `{profile.estimate.recommended_tested_ceiling_ctx}`",
        "",
        "## Stress Results",
        "",
    ]
    for result in profile.stress_results:
        if result.ok:
            lines.append(
                f"- ctx `{result.ctx_size}`: pass, tok/s `{result.tokens_per_second:.2f}`, "
                f"peak_gpu `{result.peak_gpu_use_percent}%`, peak_vram `{result.peak_vram_used_bytes}`, "
                f"unload_delta `{result.unload_delta_bytes}`"
            )
        else:
            lines.append(f"- ctx `{result.ctx_size}`: fail, error `{result.error}`")
    if failed:
        lines.extend(["", "## First Failure", "", f"- `{failed[0].ctx_size}`: `{failed[0].error}`"])
    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return characteristics_path, estimate_path, stress_path


def import_model_profile(
    config: RuntimeConfig,
    *,
    profile_root: Path,
    slug: str | None = None,
    stress_ctx_sizes: tuple[int, ...] = DEFAULT_STRESS_CTX_SIZES,
    stress_prompt: str = DEFAULT_STRESS_PROMPT,
    stress_max_tokens: int = DEFAULT_STRESS_MAX_TOKENS,
) -> ImportedModelProfile:
    characteristics = inspect_model_characteristics(config)
    stress_results = stress_test_contexts(
        config,
        ctx_sizes=stress_ctx_sizes,
        prompt=stress_prompt,
        max_tokens=stress_max_tokens,
    )
    successful = tuple(result.ctx_size for result in stress_results if result.ok)
    estimate = estimate_context(
        characteristics,
        ctx_sizes=stress_ctx_sizes,
        tested_success_ctxs=successful,
    )
    resolved_slug = slug or _slugify(characteristics.model_name)
    profile_dir = profile_root / resolved_slug
    profile = ImportedModelProfile(
        slug=resolved_slug,
        model_path=str(config.model_path),
        characteristics=characteristics,
        estimate=estimate,
        stress_results=stress_results,
        profile_dir=str(profile_dir),
    )
    write_model_profile(profile)
    return profile
