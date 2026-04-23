# Hardware And Live System Discipline

Live systems are different from code. They have state, permissions, cables,
Wi-Fi, stale processes, missing packages, and human expectations. The
supervisory method handles live systems by separating deterministic code proof
from optional real-world validation.

## Principle

Default verification must stay hardware-free. Live checks are optional evidence,
not mandatory CI.

This keeps a project maintainable when the device is offline, the network is
different, or a future contributor does not have the same hardware.

## Delegate Live Diagnostics

Live diagnostics are ideal worker tasks because they can consume time and
produce lots of environment-specific evidence. The supervisor should delegate
them with narrow permission.

A live diagnostic worker should know:

- which host or service to check
- which credentials or key path are expected
- which commands are read-only
- which logs are safe to inspect
- whether it may start or stop anything
- what final healthy state is required

## Successful Reachability Is Not Readiness

For hardware, each layer proves only one thing.

- Ping proves some network route.
- SSH proves login access.
- A listening port proves a process is bound.
- A health endpoint proves the process can answer.
- A playback command proves a specific product path.
- A human-visible display proves the complete operator experience.

Do not collapse these layers. "SSH works" does not mean the product works.

## Failure Categories

Categorize failures before fixing them.

### Network

Symptoms:

- no ping
- no route
- ARP missing
- connection timed out

Likely next checks:

- confirm IP
- inspect router/client list
- compare known-good device
- check Wi-Fi association

### Authentication

Symptoms:

- permission denied
- key rejected
- password prompt in batch mode

Likely next checks:

- correct username
- correct key path
- account exists
- authorized keys installed

### Service Down

Symptoms:

- SSH works
- health port refuses connection
- no process listening

Likely next checks:

- process list
- service logs
- startup hook
- manual start path

### Package Missing

Symptoms:

- process starts then exits
- logs say module or binary not found
- command not found

Likely next checks:

- stage package
- verify working directory
- verify dependency install
- verify interpreter path

### Command Bug

Symptoms:

- remote shell syntax error
- quoting failure
- command reports success too early
- process matcher kills wrong thing

Likely next checks:

- inspect generated command
- add regression tests
- avoid broad `pgrep -f` or `pkill -f`
- prefer explicit process identity

### Runtime Crash

Symptoms:

- command launches
- health briefly works or never works
- process exits after startup

Likely next checks:

- logs
- dependency mismatch
- port conflict
- environment variables
- display/session permissions

## Fakeable Adapters

Any code that controls hardware should have a fakeable boundary.

Examples:

- HTTP transport interface
- SSH process runner
- command builder separated from runner
- device registry abstraction
- playback agent fake

Tests should use fakes. Live scripts should be optional.

## Browser Actions Should Not Run Raw Hardware Commands

A browser should not send arbitrary shell commands or SSH directly into
hardware. The browser should send intent to the backend, such as:

- start selected receivers
- kill selected agents
- heartbeat devices
- apply next stream settings

The backend should translate that intent into constrained server-generated
commands based on predefined profiles.

## Secrets

Secrets must be runtime-only and redacted.

Rules:

- do not persist real passwords in tracked files
- do not echo passwords in logs
- do not include private key contents in reports
- do not inspect broad secret-bearing directories
- do not print password hashes
- prefer key paths over password strings
- redact response payloads

It is acceptable for local operator profiles to include a key path when that is
already expected by the project. It is not acceptable to store the key itself.

## Start/Kill Controls

Remote process controls should be conservative.

Start should:

- stage or verify required package availability
- run from the expected working directory
- be idempotent
- avoid duplicate processes
- verify the process remains alive after launch
- return per-node results

Kill should:

- target only the intended process
- avoid broad process names
- continue if one node fails
- return per-node results
- leave enough evidence for restart

When testing kill live, immediately restart and verify health unless the user
explicitly requested the service remain stopped.

## Final State Rule

Live diagnostics should leave the system in a safe final state.

Examples:

- if both agents were killed for a test, both should be restarted
- if a stream was stopped for diagnosis, report whether it was restored
- if a device cannot be restored, say so clearly and include the last known
  health state

## Sample Live Diagnostic Report

```text
garagepi2 is reachable on the network, but the product agent is down.

Evidence:
- SSH to garage2@192.168.1.241 works with the shared key.
- `ss -ltnp` shows no listener on 8080.
- `/health` returns connection refused.
- process list has no `python3 -m agent`.

Likely cause: local agent service/startup path is missing or crashed.

Least invasive next action: compare startup hook with garagepi1, stage the
agent package if missing, start the agent, then verify `/health`.
```

## Keep Live Checks Optional

Add optional scripts if useful, but make them skip by default.

Example pattern:

```bash
if [ "${PROJECT_HARDWARE_VERIFY:-0}" != "1" ]; then
  echo "skip: PROJECT_HARDWARE_VERIFY is not set to 1"
  exit 0
fi
```

This lets future agents run default verification safely without needing the
original hardware.
