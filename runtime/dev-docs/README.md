# Lattice Runtime (dev docs)

Self-defining, self-healing POSIX lattice runtime with trace-sovereign observability.

## What It Is

Lattice is a deterministic control loop that materializes FIFO ports, attaches
transport projections (via lattice-netcat), and runs processes to match a
board definition.

## Components

- `runtime/board.py`: board reader, validation, control loop
- `runtime/compiler.py`: board -> ConnectionLattice
- `runtime/reconcile.py`: POSIX reconciliation
- `runtime/health.py`: self-probing + healing
- `runtime/trace.py`: trace emission + ULP bindings
- `lattice`: CLI entrypoint
- `trace-resolve`: trace analyzer/exporter

## Core Invariants

1. Board directory is authoritative.
2. Startup is deterministic.
3. Reconcile is idempotent.
4. Ports are FIFO-first; transports are projections.

## Transport Layer

Transports are declared separately from ports and attach to FIFO ports.
Currently supported kind: `netcat`.

Example:

```json
{
  "name": "tcp-listener",
  "kind": "netcat",
  "attach": "input",
  "spec": {
    "protocol": "tcp",
    "mode": "listen",
    "port": 9999,
    "keep_open": true,
    "exec": "/bin/cat"
  }
}
```

## Kernel Gate (Optional)

Runtime can call an external `lattice-kernel` for blast-radius gating before
any POSIX reconcile. Configure via `kernel` in `board.json`.

## Examples

- `examples/simple-board`
- `examples/netcat-board`

## See Also

- `README.md`
- `TRACE-GUIDE.md`
- `docs/board-schema.md`
