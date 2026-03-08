# Lattice Runtime

Self-defining, self-healing POSIX lattice runtime.

## Overview

Lattice is a deterministic control loop that materializes FIFO ports, attaches
transport projections, and runs processes to match a declarative board.

## FIFO-First Invariant

- Every port materializes as a FIFO.
- Transports are projections that attach to FIFOs.
- The network is never authoritative; the board is.

## Installation

```bash
chmod +x lattice
sudo install -m 755 lattice /usr/local/bin/
```

The runtime requires Python 3.7+ with no external dependencies. Netcat
projections require `lattice-netcat` available on PATH.

## Board Structure

```
BOARD/
  board.json              # Main lattice definition
  peers.d/*.json          # Drop-in peer declarations (reserved)
  ports.d/*.json          # Drop-in port declarations
  transports.d/*.json     # Drop-in transport declarations
  procs.d/*.json          # Drop-in process declarations
  health.d/health.json    # Health policy
  env.d/*.sh              # Generated environment exports
  state/                  # Runtime state (sockets, traces)
```

### board.json

```json
{
  "node_id": "local",
  "socket_dir": "state/sockets",
  "ports": [],
  "transports": [],
  "procs": [],
  "health": {
    "tick_seconds": 2,
    "restart_delay": 1
  }
}
```

### Ports

Ports are structural FIFO endpoints.

```json
{
  "name": "input",
  "direction": "in",
  "path": "state/sockets/input.fifo"
}
```

### Transports (netcat)

Transports attach to FIFO ports and project bytes over TCP/UDP/SSL/Unix.

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

### Processes

```json
{
  "name": "worker",
  "command": "cat $LATTICE_PORT_INPUT > $LATTICE_PORT_OUTPUT",
  "waits": ["input"],
  "fires": ["output"],
  "env": {
    "WORKER_MODE": "fast"
  }
}
```

## Kernel Gate (Optional)

`lattice-runtime` can invoke an external `lattice-kernel` before any POSIX work.
The kernel computes blast radius and returns accept/refuse.

```json
{
  "kernel": {
    "enabled": true,
    "command": ["lattice-kernel", "analyze"],
    "policy": "kernel/policy.json",
    "fail_open": false,
    "timeout_seconds": 10
  }
}
```

## Runtime Control Loop

Each tick:

1. Read board.
2. Kernel gate (optional).
3. Compile board → ConnectionLattice.
4. Materialize FIFOs.
5. Attach transports.
6. Start processes.
7. Probe health.
8. Heal unhealthy resources.

## Health Checking

- Ports: FIFO existence and type.
- Transports: process liveness.
- Processes: exit status.

## Environment Variables

Processes receive:

- `LATTICE_NODE_ID`
- `LATTICE_SOCKET_DIR`
- `LATTICE_PORT_<NAME>` (FIFO path for waits/fires)
- `LATTICE_PORT_<NAME>_DIRECTION`
- `LATTICE_PORT_<NAME>_IN` and `LATTICE_PORT_<NAME>_OUT` for duplex ports

## Examples

- `examples/simple-board`: FIFO echo pipeline.
- `examples/netcat-board`: TCP/UDP/SSL netcat projections.
- `examples/protocol-matrix`: dynamic TCP/UDP/SSL protocol test board.

## Trace System

All runtime actions (compile, reconcile, probe, heal) emit append-only traces
with ULP bindings for algebraic analysis.

```bash
./trace-resolve state/traces/trace.log --board my-board -v
./trace-resolve state/traces/trace.log --export-ulp ulp.jsonl
./trace-resolve state/traces/trace.log --export-coxeter coxeter.json
```

## References

- Board Schema: `docs/board-schema.md`
- Runtime Contract: `docs/posix-lattice-contract.md`
- Trace Guide: `TRACE-GUIDE.md`
