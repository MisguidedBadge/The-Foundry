from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import json
import shutil
import sys

from .config import (
    ConfigError,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPTS,
    RuntimeConfig,
    validate_max_tokens,
)
from .runtime import (
    LiveModelSession,
    RuntimeVerificationError,
    build_llama_command,
    run_live_smoke,
    verify_runtime_requirements,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-gallery")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name in ("plan", "verify-runtime", "smoke-run", "interactive"):
        command_parser = subparsers.add_parser(command_name)
        command_parser.add_argument("--model")
        command_parser.add_argument("--ctx-size")
        command_parser.add_argument("--gpu-layers")
        command_parser.add_argument(
            "--allow-cpu-fallback",
            action="store_true",
            help="Rejected by design; kept only to surface a hard failure.",
        )
        if command_name in {"smoke-run", "interactive"}:
            command_parser.add_argument(
                "--prompt",
                action="append",
                dest="prompts",
                help="Repeat to provide initial prompts. Defaults vary by command.",
            )
            command_parser.add_argument(
                "--max-tokens",
                default=str(DEFAULT_MAX_TOKENS),
            )

    return parser


def build_plan_payload(config: RuntimeConfig) -> dict[str, object]:
    return {
        "command": "plan",
        "model": {
            "path": str(config.model_path),
            "exists": config.model_path.exists(),
        },
        "ctx_size": config.ctx_size,
        "runtime": {
            "backend": "llama_cpp_python",
            "python": sys.executable,
            "llama_cpp_importable": importlib.util.find_spec("llama_cpp") is not None,
            "rocm_tools": [
                {
                    "name": name,
                    "path": shutil.which(name),
                    "found": bool(shutil.which(name)),
                }
                for name in config.rocm_tools
            ],
            "gpu_layers": config.gpu_layers,
            "cpu_fallback_allowed": config.cpu_fallback_allowed,
        },
        "command_preview": build_llama_command(
            config,
            prompt=DEFAULT_PROMPTS[0],
            extra_args=["--max-tokens", str(DEFAULT_MAX_TOKENS)],
        ),
    }


def run_plan(args: argparse.Namespace) -> int:
    config = RuntimeConfig.from_sources(
        model=args.model,
        ctx_size=args.ctx_size,
        gpu_layers=args.gpu_layers,
        allow_cpu_fallback=args.allow_cpu_fallback,
    )
    print(json.dumps(build_plan_payload(config), indent=2, sort_keys=True))
    return 0


def run_verify_runtime(args: argparse.Namespace) -> int:
    config = RuntimeConfig.from_sources(
        model=args.model,
        ctx_size=args.ctx_size,
        gpu_layers=args.gpu_layers,
        allow_cpu_fallback=args.allow_cpu_fallback,
    )
    inspection = verify_runtime_requirements(config)
    payload = {
        "command": "verify-runtime",
        "status": "ok",
        "model": str(config.model_path),
        "ctx_size": config.ctx_size,
        "python": sys.executable,
        "llama_cpp_version": inspection.llama_cpp_version,
        "gpu_offload_supported": inspection.gpu_offload_supported,
        "rocm_tools": {
            status.name: status.resolved_path for status in inspection.rocm_tools
        },
        "telemetry": asdict(inspection.telemetry),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def run_smoke(args: argparse.Namespace) -> int:
    config = RuntimeConfig.from_sources(
        model=args.model,
        ctx_size=args.ctx_size,
        gpu_layers=args.gpu_layers,
        allow_cpu_fallback=args.allow_cpu_fallback,
    )
    prompts = tuple(args.prompts or DEFAULT_PROMPTS)
    max_tokens = validate_max_tokens(args.max_tokens)
    result = run_live_smoke(config, prompts=prompts, max_tokens=max_tokens)
    payload = {
        "command": "smoke-run",
        "status": "ok",
        "model": str(config.model_path),
        "ctx_size": config.ctx_size,
        "llama_cpp_version": result.llama_cpp_version,
        "before_load": asdict(result.before_load),
        "after_load": asdict(result.after_load),
        "peak_during_run": asdict(result.peak_during_run),
        "after_unload": asdict(result.after_unload),
        "unload_delta_bytes": result.unload_delta_bytes,
        "unload_within_tolerance": result.unload_within_tolerance,
        "prompts": [asdict(prompt_result) for prompt_result in result.prompts],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _print_interactive_help() -> None:
    print("Commands:")
    print("  /help       Show this help")
    print("  /telemetry  Show current GPU telemetry")
    print("  /reset      Clear chat history and keep the model loaded")
    print("  /max N      Change max output tokens for later prompts")
    print("  /exit       Unload the model and exit")


def run_interactive(args: argparse.Namespace) -> int:
    config = RuntimeConfig.from_sources(
        model=args.model,
        ctx_size=args.ctx_size,
        gpu_layers=args.gpu_layers,
        allow_cpu_fallback=args.allow_cpu_fallback,
    )
    max_tokens = validate_max_tokens(args.max_tokens)
    initial_prompts = tuple(args.prompts or ())
    current_max_tokens = max_tokens

    print(f"Loading model: {config.model_path}")
    print(f"Context size: {config.ctx_size}")
    print("GPU-only mode: enabled")
    session = LiveModelSession(config)
    print("Model loaded.")
    print(
        "Load telemetry:"
        f" device={session.after_load.hip_device_name}"
        f" gpu={session.after_load.gpu_use_percent}%"
        f" vram_used={session.after_load.vram_used_bytes}"
        f" vram_free={session.after_load.vram_free_bytes}"
    )
    _print_interactive_help()

    try:
        for prompt in initial_prompts:
            result = session.prompt(prompt, max_tokens=current_max_tokens)
            print(f"\nYou> {prompt}")
            print(f"Model> {result.output}")
            print(
                "[stats]"
                f" sane={result.sane}"
                f" tokens={result.completion_tokens}"
                f" tok/s={result.tokens_per_second:.2f}"
                f" peak_gpu={result.peak_gpu_use_percent}%"
                f" peak_vram={result.peak_vram_used_bytes}"
            )

        while True:
            try:
                prompt = input("\nYou> ").strip()
            except EOFError:
                print("\nEOF received. Exiting.")
                break
            except KeyboardInterrupt:
                print("\nInterrupted. Exiting.")
                break

            if not prompt:
                continue
            if prompt in {"/exit", "/quit"}:
                break
            if prompt == "/help":
                _print_interactive_help()
                continue
            if prompt == "/telemetry":
                telemetry = session.collect_telemetry()
                print(
                    "[telemetry]"
                    f" device={telemetry.hip_device_name}"
                    f" gpu={telemetry.gpu_use_percent}%"
                    f" vram_used={telemetry.vram_used_bytes}"
                    f" vram_free={telemetry.vram_free_bytes}"
                )
                continue
            if prompt == "/reset":
                session.reset_history()
                print("[session] Chat history reset.")
                continue
            if prompt.startswith("/max"):
                parts = prompt.split(maxsplit=1)
                if len(parts) != 2:
                    print("[session] Usage: /max N")
                    continue
                try:
                    current_max_tokens = validate_max_tokens(parts[1])
                except ConfigError as exc:
                    print(f"[session] {exc}")
                    continue
                print(f"[session] max_tokens set to {current_max_tokens}")
                continue

            result = session.prompt(prompt, max_tokens=current_max_tokens)
            print(f"Model> {result.output}")
            print(
                "[stats]"
                f" sane={result.sane}"
                f" tokens={result.completion_tokens}"
                f" tok/s={result.tokens_per_second:.2f}"
                f" peak_gpu={result.peak_gpu_use_percent}%"
                f" peak_vram={result.peak_vram_used_bytes}"
            )
            if not result.sane:
                print("[warning] Output failed the simple sanity heuristic.")
    finally:
        close_result = session.close()
        print(
            "Unload telemetry:"
            f" gpu={close_result.after_unload.gpu_use_percent}%"
            f" vram_used={close_result.after_unload.vram_used_bytes}"
            f" vram_free={close_result.after_unload.vram_free_bytes}"
        )
        print(
            "Unload check:"
            f" delta_bytes={close_result.unload_delta_bytes}"
            f" within_tolerance={close_result.unload_within_tolerance}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            return run_plan(args)
        if args.command == "verify-runtime":
            return run_verify_runtime(args)
        if args.command == "smoke-run":
            return run_smoke(args)
        if args.command == "interactive":
            return run_interactive(args)
    except (ConfigError, RuntimeVerificationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
