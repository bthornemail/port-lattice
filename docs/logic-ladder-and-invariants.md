# Logic Ladder and Seven Invariants

This document maps the conceptual logic ladder to what `port-lattice` implements today.

## 1) Logic ladder (conceptual stack)

The project language points to progression across:

- propositional logic
- first-order logic
- second-order logic
- higher-order logic
- grammar systems
- concurrent constraint logic
- rule engines

## 2) Seven invariants as metastructure

In this repository, the best operational reading is:

- **Type theory / axioms**: admissibility boundary (what declarations are well-formed).
- **BICF / rules / constraints**: interaction discipline (board validation + reconcile constraints).
- **Geometry**: continuity and adjacency across ports/transports/process flow.
- **Hypergraph**: structural organization of multi-entity relations in board topology.
- **Provenance**: append-only trace with board hashes and event lineage.
- **Federation**: peer/transport patterns enabling multi-node exchange (without authority merge here).
- **Projection surfaces**: observable runtime state (`health.json`, traces, exported env, network sockets/FIFOs).

These are not alternatives to logic; they are the envelope that different logical orders inhabit.

## 3) Constitutional split for contributors

Use this architectural split when designing or reviewing changes:

- **Constitutional basis**
  - type theory / axioms
  - boundaries / BICF
- **Structural basis**
  - geometry
  - hypergraph
- **Historical/distributed basis**
  - provenance
  - federation
- **Observable basis**
  - projection surfaces

## 4) Grounding in current code

Current code directly implements parts of this map:

- Type/boundary discipline: board parsing and validation rules (`runtime/runtime/board.py`, `netcat/runtime/board.py`).
- Rule-constrained interaction: compile/reconcile/heal state machine (`runtime/runtime/compiler.py`, `runtime/runtime/reconcile.py`, `runtime/runtime/health.py`).
- Provenance: immutable trace emission and hash attribution (`runtime/runtime/trace.py`, `netcat/runtime/trace_schema.py`).
- Federation substrate: peers, netcat transports, seam digest pull (`runtime/runtime/types.py`, `netcat/runtime/seam_transport.py`).
- Projection surfaces: `state/health.json`, `state/traces/trace.log`, `env.d/*.sh`.

Not fully implemented in this repo:

- A general theorem prover or typed proof assistant.
- Authoritative distributed merge semantics (explicitly out of transport scope).
- Higher-order reasoning engines beyond ULP-style event bindings and manifest constraints.
