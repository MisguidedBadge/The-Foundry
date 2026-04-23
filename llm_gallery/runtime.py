from __future__ import annotations

import gc
import importlib
import json
import shutil
import subprocess
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from .config import ConfigError, DEFAULT_SYSTEM_PROMPT, RuntimeConfig
from .sanity import output_is_sane


class RuntimeVerificationError(RuntimeError):
    """Raised when ROCm or llama.cpp runtime requirements are not satisfied."""


@dataclass(frozen=True)
class ToolStatus:
    name: str
    resolved_path: str | None
    ok: bool


@dataclass(frozen=True)
class GpuTelemetry:
    hip_device_name: str
    gpu_use_percent: int
    vram_total_bytes: int
    vram_used_bytes: int
    vram_free_bytes: int


@dataclass(frozen=True)
class PromptResult:
    prompt: str
    output: str
    sane: bool
    elapsed_seconds: float
    completion_tokens: int
    tokens_per_second: float
    peak_gpu_use_percent: int
    peak_vram_used_bytes: int


@dataclass(frozen=True)
class RuntimeInspection:
    python_executable: ToolStatus
    llama_cpp_version: str
    gpu_offload_supported: bool
    rocm_tools: tuple[ToolStatus, ...]
    telemetry: GpuTelemetry


@dataclass(frozen=True)
class SmokeRunResult:
    llama_cpp_version: str
    before_load: GpuTelemetry
    after_load: GpuTelemetry
    peak_during_run: GpuTelemetry
    after_unload: GpuTelemetry
    prompts: tuple[PromptResult, ...]
    unload_delta_bytes: int
    unload_within_tolerance: bool


@dataclass(frozen=True)
class SessionCloseResult:
    after_unload: GpuTelemetry
    unload_delta_bytes: int
    unload_within_tolerance: bool


ROCM_SMI_ARGS = (
    "rocm-smi",
    "--showproductname",
    "--showuse",
    "--showmeminfo",
    "vram",
    "--json",
)
ROCMINFO_ARGS = ("rocminfo",)
UNLOAD_TOLERANCE_BYTES = 256 * 1024 * 1024
SAMPLING_INTERVAL_SECONDS = 0.25


def build_llama_command(
    config: RuntimeConfig,
    *,
    prompt: str,
    extra_args: list[str] | None = None,
) -> list[str]:
    enforce_gpu_only(config)
    command = [
        ".venv/bin/python",
        "-m",
        "llm_gallery.cli",
        "smoke-run",
        "--model",
        str(config.model_path),
        "--ctx-size",
        str(config.ctx_size),
        "--gpu-layers",
        str(config.gpu_layers),
        "--prompt",
        prompt,
    ]
    if extra_args:
        command.extend(extra_args)
    return command


def enforce_gpu_only(config: RuntimeConfig) -> None:
    if config.cpu_fallback_allowed:
        raise ConfigError("CPU fallback is forbidden; disable LLM_GALLERY_ALLOW_CPU_FALLBACK")
    if config.gpu_layers == 0 or config.gpu_layers < -1:
        raise ConfigError("GPU offload must be enabled; configure gpu-layers to -1 or > 0")


def _run_text_command(
    args: Sequence[str],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return run(
        list(args),
        capture_output=True,
        check=True,
        text=True,
    )


def _extract_json_blob(output: str) -> dict[str, Any]:
    start = output.find("{")
    if start < 0:
        raise RuntimeVerificationError("failed to parse JSON output from rocm-smi")
    return json.loads(output[start:])


@lru_cache(maxsize=1)
def _extract_hip_device_name(
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    result = _run_text_command(ROCMINFO_ARGS, run=run)
    blocks: list[list[str]] = []
    current_block: list[str] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("Agent ") and current_block:
            blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    for block in blocks:
        if not any(line.startswith("Device Type:") and line.endswith("GPU") for line in block):
            continue
        for line in block:
            if line.startswith("Marketing Name:"):
                return line.split(":", 1)[1].strip()
        for line in block:
            if line.startswith("Name:"):
                return line.split(":", 1)[1].strip()
    raise RuntimeVerificationError("failed to determine HIP-visible device name from rocminfo")


def collect_gpu_telemetry(
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GpuTelemetry:
    result = _run_text_command(ROCM_SMI_ARGS, run=run)
    payload = _extract_json_blob(result.stdout)
    card_key = sorted(payload)[0]
    card = payload[card_key]
    total_bytes = int(card["VRAM Total Memory (B)"])
    used_bytes = int(card["VRAM Total Used Memory (B)"])
    return GpuTelemetry(
        hip_device_name=_extract_hip_device_name(run=run),
        gpu_use_percent=int(card["GPU use (%)"]),
        vram_total_bytes=total_bytes,
        vram_used_bytes=used_bytes,
        vram_free_bytes=max(total_bytes - used_bytes, 0),
    )


def _load_llama_cpp() -> Any:
    try:
        return importlib.import_module("llama_cpp")
    except ImportError as exc:
        raise RuntimeVerificationError(
            "llama_cpp is not available in the current Python environment"
        ) from exc


def _sample_telemetry_during(
    operation: Callable[[], Any],
    *,
    telemetry_fn: Callable[[], GpuTelemetry],
) -> tuple[Any, list[GpuTelemetry]]:
    samples: list[GpuTelemetry] = []
    stop_event = threading.Event()

    def sample_loop() -> None:
        while not stop_event.is_set():
            try:
                samples.append(telemetry_fn())
            except Exception:
                pass
            stop_event.wait(SAMPLING_INTERVAL_SECONDS)

    thread = threading.Thread(target=sample_loop, daemon=True)
    thread.start()
    try:
        return operation(), samples
    finally:
        stop_event.set()
        thread.join(timeout=1.0)


def _peak_telemetry(samples: Sequence[GpuTelemetry], fallback: GpuTelemetry) -> GpuTelemetry:
    if not samples:
        return fallback
    return max(samples, key=lambda sample: (sample.vram_used_bytes, sample.gpu_use_percent))


def unload_within_tolerance(
    before_load: GpuTelemetry,
    after_unload: GpuTelemetry,
    *,
    tolerance_bytes: int = UNLOAD_TOLERANCE_BYTES,
) -> tuple[int, bool]:
    delta = after_unload.vram_used_bytes - before_load.vram_used_bytes
    return delta, delta <= tolerance_bytes


def inspect_runtime(
    config: RuntimeConfig,
    *,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> RuntimeInspection:
    rocm_statuses = tuple(
        ToolStatus(name=name, resolved_path=which(name), ok=bool(which(name)))
        for name in config.rocm_tools
    )
    missing = [status.name for status in rocm_statuses if not status.ok]
    if missing:
        raise RuntimeVerificationError(
            "missing ROCm tools: " + ", ".join(sorted(missing))
        )
    llama_cpp = _load_llama_cpp()
    telemetry = collect_gpu_telemetry(run=run)
    python_path = shutil.which("python3") or shutil.which("python")
    return RuntimeInspection(
        python_executable=ToolStatus(
            name="python",
            resolved_path=python_path,
            ok=bool(python_path),
        ),
        llama_cpp_version=getattr(llama_cpp, "__version__", "unknown"),
        gpu_offload_supported=bool(llama_cpp.llama_supports_gpu_offload()),
        rocm_tools=rocm_statuses,
        telemetry=telemetry,
    )


def verify_runtime_requirements(
    config: RuntimeConfig,
    *,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> RuntimeInspection:
    enforce_gpu_only(config)
    inspection = inspect_runtime(config, which=which, run=run)
    if not inspection.gpu_offload_supported:
        raise RuntimeVerificationError("llama.cpp backend does not report GPU offload support")
    return inspection


def run_live_smoke(
    config: RuntimeConfig,
    *,
    prompts: Sequence[str],
    max_tokens: int,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    clock: Callable[[], float] = time.perf_counter,
) -> SmokeRunResult:
    session = LiveModelSession(config, run=run, clock=clock)
    prompt_results: list[PromptResult] = []
    peak_during_run = session.after_load
    try:
        for prompt in prompts:
            result = session.prompt(prompt, max_tokens=max_tokens)
            if not result.sane:
                raise RuntimeVerificationError(
                    f"model output failed sanity check for prompt: {prompt}"
                )
            prompt_results.append(result)
            peak_during_run = max(
                [peak_during_run, session.collect_telemetry()],
                key=lambda sample: (sample.vram_used_bytes, sample.gpu_use_percent),
            )
    finally:
        close_result = session.close()

    return SmokeRunResult(
        llama_cpp_version=session.llama_cpp_version,
        before_load=session.before_load,
        after_load=session.after_load,
        peak_during_run=peak_during_run,
        after_unload=close_result.after_unload,
        prompts=tuple(prompt_results),
        unload_delta_bytes=close_result.unload_delta_bytes,
        unload_within_tolerance=close_result.unload_within_tolerance,
    )


class LiveModelSession:
    def __init__(
        self,
        config: RuntimeConfig,
        *,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._config = config
        self._run = run
        self._clock = clock
        self._inspection = verify_runtime_requirements(config, run=run)
        self.llama_cpp_version = self._inspection.llama_cpp_version
        self.before_load = self._inspection.telemetry
        self._llama_cpp = _load_llama_cpp()
        self._llm = self._llama_cpp.Llama(
            model_path=str(config.model_path),
            n_gpu_layers=config.gpu_layers,
            n_ctx=config.ctx_size,
            use_mmap=False,
            offload_kqv=True,
            verbose=False,
        )
        self._install_direct_chat_handler()
        self.after_load = collect_gpu_telemetry(run=run)
        self._closed = False
        self._messages: list[dict[str, str]] = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
        ]

    @property
    def config(self) -> RuntimeConfig:
        return self._config

    def collect_telemetry(self) -> GpuTelemetry:
        return collect_gpu_telemetry(run=self._run)

    def reset_history(self) -> None:
        self._messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]

    def _install_direct_chat_handler(self) -> None:
        template = self._llm.metadata.get("tokenizer.chat_template")
        if not template:
            return

        llama_chat_format = importlib.import_module("llama_cpp.llama_chat_format")
        eos_token_id = self._llm.token_eos()
        bos_token_id = self._llm.token_bos()
        eos_token = (
            self._llm._model.token_get_text(eos_token_id) if eos_token_id != -1 else ""
        )
        bos_token = (
            self._llm._model.token_get_text(bos_token_id) if bos_token_id != -1 else ""
        )

        class DirectJinja2ChatFormatter(llama_chat_format.Jinja2ChatFormatter):
            def __call__(self, *, messages: list[dict[str, Any]], functions=None, function_call=None, tools=None, tool_choice=None, **kwargs: Any):
                def raise_exception(message: str):
                    raise ValueError(message)

                prompt = self._environment.render(
                    messages=messages,
                    eos_token=self.eos_token,
                    bos_token=self.bos_token,
                    raise_exception=raise_exception,
                    add_generation_prompt=self.add_generation_prompt,
                    functions=functions,
                    function_call=function_call,
                    tools=tools,
                    tool_choice=tool_choice,
                    strftime_now=self.strftime_now,
                    enable_thinking=False,
                    preserve_thinking=False,
                    add_vision_id=False,
                )

                return llama_chat_format.ChatFormatterResponse(
                    prompt=prompt,
                    stop=[self.eos_token],
                    stopping_criteria=None,
                    added_special=True,
                )

        formatter = DirectJinja2ChatFormatter(
            template=template,
            eos_token=eos_token,
            bos_token=bos_token,
            stop_token_ids=[eos_token_id],
        )
        self._llm.chat_handler = formatter.to_chat_handler()
        self._llm.chat_format = None

    @staticmethod
    def _clean_chat_output(text: str) -> str:
        output = text.strip()
        if output.startswith("<think>") and "</think>" in output:
            output = output.split("</think>", 1)[1].strip()
        return output

    def prompt(self, prompt: str, *, max_tokens: int) -> PromptResult:
        if self._closed:
            raise RuntimeVerificationError("session is already closed")

        def generate() -> Any:
            return self._llm.create_chat_completion(
                messages=self._messages + [{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.2,
                top_p=0.9,
                repeat_penalty=1.05,
                stream=False,
            )

        started = self._clock()
        completion, samples = _sample_telemetry_during(
            generate,
            telemetry_fn=self.collect_telemetry,
        )
        elapsed = max(self._clock() - started, 1e-9)
        output = self._clean_chat_output(
            completion["choices"][0]["message"]["content"] or ""
        )
        usage = completion.get("usage", {})
        completion_tokens = int(usage.get("completion_tokens") or 0)
        if completion_tokens <= 0:
            completion_tokens = len(output.split())
        peak = _peak_telemetry(samples, self.after_load)
        result = PromptResult(
            prompt=prompt,
            output=output,
            sane=output_is_sane(output),
            elapsed_seconds=elapsed,
            completion_tokens=completion_tokens,
            tokens_per_second=completion_tokens / elapsed,
            peak_gpu_use_percent=peak.gpu_use_percent,
            peak_vram_used_bytes=peak.vram_used_bytes,
        )
        self._messages.append({"role": "user", "content": prompt})
        self._messages.append({"role": "assistant", "content": output})
        return result

    def close(self) -> SessionCloseResult:
        if self._closed:
            after_unload = self.collect_telemetry()
            unload_delta, unload_ok = unload_within_tolerance(
                self.before_load,
                after_unload,
            )
            return SessionCloseResult(
                after_unload=after_unload,
                unload_delta_bytes=unload_delta,
                unload_within_tolerance=unload_ok,
            )

        self._llm.close()
        del self._llm
        gc.collect()
        time.sleep(1.0)
        self._closed = True
        after_unload = self.collect_telemetry()
        unload_delta, unload_ok = unload_within_tolerance(
            self.before_load,
            after_unload,
        )
        return SessionCloseResult(
            after_unload=after_unload,
            unload_delta_bytes=unload_delta,
            unload_within_tolerance=unload_ok,
        )
