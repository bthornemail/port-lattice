# Lattice Trace System Guide

## Overview

The lattice runtime implements **trace-sovereign computing** with a Coxeter-style
chain complex. Every runtime action is recorded as an immutable trace event with
ULP (Universal Logos Protocol) bindings, enabling algebraic analysis and
geometric interpretation of system behavior.

## Core Concepts

### Blackboard Pattern

The trace log (`state/traces/trace.log`) is an append-only blackboard:
- Writers only append events.
- Readers consume independently.
- No coordination required.
- Fully reproducible from log.

### ULP Bindings

Each trace event is represented as a polynomial over atoms:

```json
{
  "version": "ulp-calculus-1.0",
  "procedure": "runtime_tick",
  "interrupt": "event::reconcile",
  "result": "+1*runtime +1*event_reconcile +1*resource_input +1*action_port_materialized",
  "atoms": ["runtime", "event_reconcile", "resource_input", "action_port_materialized"],
  "hash": "1ff05f6ba994e7f7"
}
```

### Coxeter Structure

The topology forms a chain complex:
- **0-cells (vertices)**: atoms (ports, transports, processes)
- **1-cells (edges)**: dependencies (waits/fires)
- **2-cells (faces)**: composed procedures

## Trace Event Types

### compile

Board compilation into ConnectionLattice.

```json
{
  "type": "compile",
  "payload": {
    "action": "compile",
    "num_fifos": 2,
    "num_transports": 1,
    "num_processes": 1
  }
}
```

### reconcile

POSIX resource creation/update/deletion.

```json
{
  "type": "reconcile",
  "payload": {
    "resource": "input",
    "action": "port_materialized"
  }
}
```

Actions:
- `port_materialized` - FIFO created
- `transport_attached` - transport projection started
- `transport_detached` - transport projection stopped
- `process_started` - process spawned

### kernel

Kernel gate decisions before POSIX reconcile.

Actions:
- `blast_analyzed`
- `blast_refused`
- `blast_accepted`

### probe

Health check of resource.

```json
{
  "type": "probe",
  "payload": {
    "resource": "echo-worker",
    "status": "healthy"
  }
}
```

Status values:
- `healthy`
- `unhealthy`
- `unknown`
- `warming`

Probe payloads may include optional fields:
- `last_accept_age_ms`: milliseconds since last successful accept (ephemeral mode).

### heal

Automatic healing of unhealthy resource.

```json
{
  "type": "heal",
  "payload": {
    "resource": "tcp-listener",
    "action": "restart_transport"
  }
}
```

Actions:
- `port_rematerialized`
- `restart_transport`
- `restart_process`

### validate_error

Board validation failure.

### warnings

Non-fatal warnings (drop-in collisions, overrides).

## Using trace-resolve

```bash
./trace-resolve state/traces/trace.log
./trace-resolve state/traces/trace.log --board ./my-board
./trace-resolve state/traces/trace.log --export-ulp state/traces/ulp.jsonl
./trace-resolve state/traces/trace.log --export-coxeter state/traces/coxeter.json
```
