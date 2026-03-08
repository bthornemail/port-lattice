# Port-Lattice: Actual Functionality (Contributor Reference)

## 1) What this repo is

`port-lattice` is a transport/runtime workspace that combines:

- `runtime/`: FIFO-first board runtime (Python).
- `netcat/`: POSIX `lattice-netcat` transport binary and a second board runtime.
- `kernel/`: developer notes only in this repository (no executable kernel code here).

Primary scope in code:

- Materialize local FIFO ports from declarative board files.
- Attach byte transports (mostly via `lattice-netcat`).
- Run and supervise declared processes.
- Emit append-only trace events with ULP bindings.
- Perform local health probing and simple self-healing.

Out of scope in this repository:

- Event interpretation/authority decisions on domain state.
- Merge/replay semantics for distributed truth (referenced as external concerns).

## 2) Top-level architecture

There are two runnable lattice CLIs in this repo:

- `runtime/lattice` (newer FIFO-direction model: `in|out|inout`, transport sections, optional kernel gate).
- `netcat/lattice` (older/alternate model: `port.type` such as `fifo`, `tcp`, `ssh_forward`).

Both are active code paths and both are tested in `test.sh`.

## 3) Runtime behavior (`runtime/`)

Main entry:

- `./runtime/lattice run <board-dir> [--once]`
- `./runtime/lattice validate <board-dir>`

Board load and validation:

- Reads `board.json` plus drop-ins from `peers.d`, `ports.d`, `transports.d`, `procs.d`.
- Loads health policy from `health.d/health.json` when present.
- Validates duplicate names, transport attachment correctness, protocol/mode constraints, and process port references.

Control loop each tick:

1. Reload board from disk (supports live edits).
2. Compute board hash and trace generation.
3. Optional external kernel gate (`kernel.command`) before POSIX reconciliation.
4. Compile board into in-memory `ConnectionLattice`.
5. Generate shell exports in `env.d/*.sh`.
6. Reconcile:
   - create FIFOs,
   - start/replace `lattice-netcat` transports,
   - start missing declared processes.
7. Probe health and write `state/health.json`.
8. Heal resources marked unhealthy (restart/recreate with delay threshold).

Tracing:

- Appends NDJSON events to `state/traces/trace.log`.
- Event types include: `compile`, `reconcile`, `probe`, `heal`, `kernel`, `validate_error`, `warnings`.
- Each event contains an algebraic ULP binding payload.
- `runtime/trace-resolve` validates trace structure and can export ULP/Coxeter views.

## 4) Transport behavior (`netcat/`)

`lattice-netcat` (`netcat/lattice-netcat`) is a POSIX shell transport tool with:

- TCP/UDP/SSL/Unix modes.
- listen/connect behavior.
- optional `exec` command hook.
- FIFO integration, PID/log options, scan mode.
- implementation preference for host tools (`nc`, `socat`, `openssl`) with fallbacks.

Seam envelope mover:

- `netcat/seam-transport` wraps `netcat/runtime/seam_transport.py`.
- Protocol is intentionally minimal:
  - server sends `MANIFEST sha256:<hash> count=<n>`,
  - client sends `GET` (or `NOOP`),
  - pull verifies digest and count after transfer.
- It moves NDJSON bytes and does not merge/interpret events.

## 5) Alternate runtime behavior (`netcat/runtime`)

Main entry:

- `./netcat/lattice run|validate|trace-resolve ...`

Differences from `runtime/` model:

- Uses `port.type` semantics (`fifo`, `tcp`, `udp`, `unix`, `ssl`, `ssh_forward`).
- Manages PID files for processes and SSH forwards.
- Health probing is port-type driven; healing restarts missing pids or rematerializes FIFO.
- Trace format is compatible at high level (`lattice-trace-1`) but implementation is separate.

This path is useful for compatibility and netcat-focused workflows, but it is a distinct implementation.

## 6) Contributor map: where to edit

- Board parsing/validation/control loop (`runtime`): `runtime/runtime/board.py`
- Board->lattice compile (`runtime`): `runtime/runtime/compiler.py`
- Reconciliation logic (`runtime`): `runtime/runtime/reconcile.py`
- Health and healing (`runtime`): `runtime/runtime/health.py`
- Trace emission and board hash (`runtime`): `runtime/runtime/trace.py`
- Optional kernel gate adapter: `runtime/runtime/kernel_adapter.py`
- POSIX transport script: `netcat/lattice-netcat`
- Seam transport protocol mover: `netcat/runtime/seam_transport.py`
- Legacy/alternate runtime engine: `netcat/runtime/board.py`

## 7) Verified local commands

From repo root:

```bash
./runtime/lattice validate runtime/examples/simple-board
./runtime/lattice run runtime/examples/simple-board --once
./netcat/lattice validate netcat/examples/board
./netcat/lattice run netcat/examples/board --once
./netcat/lattice trace-resolve netcat/examples/board/state/traces/trace.log --board netcat/examples/board
```

Combined test harness:

```bash
./test.sh
```

## 8) Practical boundaries and caveats

- `kernel/` here is documentation only; runtime kernel decisions require an external command (`lattice-kernel`) on PATH.
- Two runtime implementations are present; contributors should state explicitly which runtime path they are modifying.
- `runtime/reconcile.py` starts subprocesses with `stdout/stderr` piped; there is no built-in log rotation/collection yet.
- Distributed anti-entropy in this repo remains transport-level; authoritative merge/replay is intentionally externalized.
