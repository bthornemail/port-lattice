# POSIX Lattice Runtime Contract

This document defines the core abstractions and runtime contract for a
self-probing, self-healing lattice that runs in POSIX environments.

## Core Abstractions

- Board: on-disk source of truth describing peers, ports, transports, processes, and health.
- ConnectionLattice: compiled in-memory representation of the board.
- Runtime: a deterministic control loop that converges POSIX resources to match
  the ConnectionLattice, probes health, and heals failures.

## FIFO-First Invariant

- Every port materializes as a FIFO.
- Network transports are projections that attach to FIFOs.
- The network is never authoritative; the board is.

## Runtime Loop (Tick)

1. Read board.
2. Kernel gate (optional, external lattice-kernel).
3. Compile to ConnectionLattice.
4. Materialize FIFOs (ports).
5. Attach transports (projections).
6. Start processes.
7. Probe health of ports, transports, and processes.
8. Heal unhealthy resources by recreating them.

## POSIX Substrate

- FIFOs: `mkfifo` for structural ports.
- Projections: `lattice-netcat` for TCP/UDP/SSL/Unix stream projection.
- Processes: spawned with env exports derived from the board.

## Health Probing Contract

- Port probes are FIFO-only and must be non-destructive.
- Transport probes validate process liveness, not network availability.
- Probe results are recorded in runtime state for the next reconcile pass.

## Healing Contract

- Missing FIFO is a structural fault and must be recreated.
- Failed transport processes are restarted.
- Failed processes are restarted.
- Restart delay is controlled by the health policy.

## Observability

- Runtime emits traces for key events: compile, reconcile, probe, heal.
- Trace actions are structural (port materialized, transport attached).
