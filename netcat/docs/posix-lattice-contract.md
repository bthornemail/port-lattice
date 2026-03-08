# POSIX Lattice Runtime Contract

This document defines the core abstractions and runtime contract for a
self-probing, self-healing lattice that runs in POSIX environments.

## Core Abstractions

- Board: on-disk source of truth describing peers, ports, processes, and health.
- ConnectionLattice: compiled in-memory representation of the board.
- Runtime: a deterministic control loop that converges POSIX resources to match
  the ConnectionLattice, probes health, and heals failures.

## Invariants

- Authority: the board directory is authoritative; runtime does not invent state.
- Determinism: given the same board, startup order is fixed and reproducible.
- Idempotency: reconcile loop must be safe to run repeatedly.
- Healing scope: only transport/process availability is healed, not semantics.

## Runtime Loop (Tick)

1. Read board.
2. Compile to ConnectionLattice.
3. Reconcile POSIX resources (FIFOs, sockets, tunnels, processes).
4. Probe health of transports and processes.
5. Heal unhealthy resources by recreating them.

## POSIX Substrate

- FIFOs: mkfifo for local edges.
- Unix sockets / TCP / UDP: lattice-netcat, socat, or system netcat.
- SSH forwards: ssh -L with pid tracking.
- Processes: spawned with env exports derived from board.

## Health Probing Contract

- Transport probes must be non-destructive, bounded by timeouts.
- Probing must report "healthy" only after successful open + I/O test.
- Probe results are recorded in runtime state for the next reconcile pass.

## Healing Contract

- On unhealthy resource, terminate and recreate the resource.
- Health map must be cleared after successful heal.
- Restart delay is controlled by health policy.

## Observability

- Runtime emits traces for key events: compile, reconcile, probe, heal.
- Traces must be self-describing so they can be resolved later.
- Trace schema: `docs/trace-schema.md`.

## Runtime State Files

- `state/health.json`: last probe status per resource with timestamps.
- `state/traces/trace.log`: JSON lines of runtime events.
