# Guardrails

This file records repeatable anti-patterns and safety rules learned during the
project. Add a guardrail only when it is likely to prevent a future mistake.

## Scope

- Work only on the active task unless the user explicitly expands scope.
- Do not add future-milestone features opportunistically.
- Do not refactor unrelated code during focused fixes.

## Verification

- Do not claim success while required verification is red.
- Keep default verification deterministic and hardware-free.
- Keep optional live checks separate from default tests.

## Safety

- Do not persist real secrets in tracked files.
- Do not print private keys, tokens, passwords, or password hashes.
- Do not run destructive commands without explicit user approval.

## Worker Coordination

- Do not assign overlapping write ownership.
- Do not accept worker claims without reviewing diff and evidence.
- Close stalled workers before reassigning the same lane.
