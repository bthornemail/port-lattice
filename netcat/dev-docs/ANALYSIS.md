# Rumsfeld Analysis: POSIX Network Lattice

A systematic categorization of implementation certainty for the self-defining, self-healing network lattice.

---

## Known Knowns
*Things we know that we know - proven, implemented, working*

### Runtime Infrastructure (80% complete)
- **Self-healing loop exists**: health check → mark unhealthy → heal by recreating handles → clear health map
- **POSIX substrate works**: FIFOs, Unix sockets, SSH tunnels, process spawning all proven
- **Deterministic startup**: fixed order (create FIFOs → create transports → start processes)
- **Transport layer**: `lattice-netcat` implemented with TCP/UDP/Unix/SSL/FIFO/exec modes
- **Tool fallback chain**: nc → socat → portable implementations
- **SSH tunnel machinery**: working with unique socket path fix (`/tmp/lattice-ssh-<uniqueId>.sock`)
- **Health probing contract**: non-destructive, timeout-bounded, open+I/O test for "healthy" signal
- **Observability**: POSIX-native debugging (mkfifo/socat/ps/lsof/ssh work)
- **Ops surface**: Makefile build/test/run/release pipeline
- **PID/log integration**: runtime can track process state

### Architecture Principles
- **Board as authority**: single source of truth (files, not code)
- **Deterministic compilation**: board → ConnectionLattice is reproducible
- **Idempotent reconciliation**: safe to run reconcile loop repeatedly
- **Healing scope bounded**: only transport/process availability, never semantics
- **Projection model**: POSIX is substrate, runtime mediates, board is ground truth

### Schema Design
- **Board structure**: directory tree with JSON definitions
- **Separation of concerns**: peers.d/, ports.d/, procs.d/, health.d/ for declarations; env.d/, state/ for generated artifacts
- **Peer declarations**: host/user/port/key/options defined
- **Port types**: FIFO, SSH forward, Unix socket, TCP, UDP
- **Process specs**: command, waits (dependencies), fires (outputs), env overrides
- **Health policy**: tick_seconds, restart_delay configurable

---

## Known Unknowns
*Things we know that we don't know - identified gaps requiring decisions*

### Compilation Pipeline
- **Board reader implementation**: need `readBoard :: FilePath -> IO Board` that parses JSON + drop-ins
- **Drop-in merge semantics**: how do peers.d/*.json files compose? Last-write-wins? Error on collision?
- **Validation layer**: when/where to validate board (compile-time? runtime? both?)
- **Error propagation**: how should compiler handle malformed JSON, missing SSH keys, circular dependencies?
- **Incremental compilation**: full recompile every tick, or diff-based updates?

### Reconciliation Logic
- **Diff algorithm**: how to compute ConnectionLattice deltas (old vs new)?
- **Resource lifecycle**: what's the exact sequence for stopping removed processes (SIGTERM → wait → SIGKILL)?
- **Atomicity boundaries**: which reconcile actions must be atomic? Which can partially succeed?
- **Rollback strategy**: if reconcile fails mid-way, do we attempt rollback or converge forward?
- **State persistence**: does runtime state/ survive restarts? Should it?

### Peer Topology
- **Peer discovery**: static declarations only, or dynamic peer addition?
- **SSH key management**: board references paths - what if keys don't exist? Generate? Fail?
- **Tunnel multiplexing**: can multiple ports share one SSH connection?
- **Peer health**: do we probe SSH tunnel liveness? How often?
- **NAT traversal**: if peers are behind NAT, what's the strategy? (probably out of scope for v1)

### Process Environment
- **Env export generation**: exact algorithm for `env.d/00-lattice.sh` from board
- **Variable naming**: `LATTICE_PORT_INPUT` vs `LATTICE_FIFO_INPUT` vs custom naming?
- **Env composition**: if procs.d/ override variables, what's the precedence order?
- **Dynamic env updates**: if board changes, do running processes get new env? (probably no, but clarify)

### Concurrency & Timing
- **Tick rate**: 2 seconds is default - is this always safe? Too fast for some operations?
- **Race conditions**: can reconcile and health-check conflict?
- **Lock files**: do we need lattice-wide locks for state/ writes?
- **Startup transients**: how long to wait for "system stable" before first health check?

### Testing Strategy
- **Board test fixtures**: need minimal/medium/complex example boards
- **Integration test harness**: how to test full reconcile loop without real SSH?
- **Failure injection**: how to test healing (kill transports mid-run)?
- **Cross-platform validation**: does this work on BSD, macOS, Linux?

---

## Unknown Knowns
*Things we don't know that we know - implicit knowledge not yet formalized*

### Architectural Patterns Already Present
- **You've built reconciliation loops before**: in Tetragrammatron-OS ("deterministic worlds from append-only events")
- **Connection management patterns**: your 40+ projects likely contain working examples of FIFO/socket lifecycle
- **JSON parsing in shell/TypeScript**: you've done this in existing codebases
- **Process supervision**: you run systems "unattended" in your van - those patterns apply here

### Domain Knowledge Not Captured
- **SSH tunnel failure modes**: you've debugged these in real deployments - what breaks most often?
- **POSIX tool quirks**: you know which `nc` flags work on which platforms from testing `lattice-netcat`
- **Timing heuristics**: you probably have intuition for "2 seconds is safe for most FIFO opens" from experience
- **Error patterns**: which board schema mistakes will users make most often?

### Design Decisions Already Made (but not written down)
- **Why JSON not YAML/TOML**: (probably portability + parsability in shell)
- **Why directory-per-resource-type**: (probably because filesystem = natural namespace)
- **Why not systemd units**: (probably POSIX portability + determinism)
- **Why health-then-heal not heal-on-detect**: (probably to avoid flapping)

---

## Unknown Unknowns
*Things we don't know that we don't know - risks and emergent complexity*

### Operational Mysteries
- **What breaks in month 6?**: transient bugs that only appear after extended runtime
- **What performance cliff exists?**: does this scale to 100 peers? 1000 processes?
- **What debugging blind spots?**: which failure modes are invisible to POSIX tools?
- **What user mental model mismatches?**: how will operators misunderstand the board abstraction?

### Emergent Behavior
- **Cascade failures**: does one unhealthy transport trigger others? Oscillations?
- **Resource exhaustion**: file descriptor limits, PID limits, socket buffer limits
- **Clock skew**: if system clock jumps, does health loop misbehave?
- **Disk full**: what happens when state/ can't write?

### Integration Surprises
- **Firewall interactions**: how do various firewalls interact with SSH tunnels?
- **Container environments**: does this work in Docker? Podman? LXC?
- **Init system conflicts**: does this fight with systemd/runit/s6?
- **Network topology changes**: what if DNS fails? Routes change? Interfaces go down?

### Security Unknowns
- **Privilege escalation vectors**: can malicious board files escape containment?
- **Secrets in board files**: are SSH keys in plaintext acceptable? Encrypted?
- **Process isolation**: if one process compromised, can it poison the lattice?
- **Audit trail**: do we need cryptographic proofs of board changes?

### Philosophical Edge Cases
- **Board updates during reconcile**: what if board changes mid-tick?
- **Circular dependencies**: procs wait on each other - who starts first?
- **Undefined vs null vs absent**: JSON null vs missing key vs empty string semantics?
- **Identity over time**: if peer "edge" is redefined, is it the same peer?

---

## Strategic Recommendations

### Ship v1.1 with Known Knowns + Resolved Known Unknowns
**Minimum viable self-defining lattice:**
1. Implement board reader (JSON parse + drop-in merge with last-write-wins)
2. Implement compiler (board → ConnectionLattice, fail-fast on validation errors)
3. Implement reconcile loop (full recompile each tick, idempotent POSIX actions)
4. Generate env.d/00-lattice.sh with standard variable names
5. Use existing health/heal loop (already working)
6. Document one known-good board example

**Defer to v1.2+:**
- Incremental compilation
- Dynamic peer discovery
- Tunnel multiplexing
- Advanced concurrency handling

### Instrument for Unknown Unknowns
**Build in observability from day 1:**
- Trace every compile/reconcile/probe/heal event with timestamps
- Log board deltas on each tick
- Track resource creation/deletion counts
- Expose health map as readable state file
- Make tick duration tunable via board (not hardcoded)

**Plan for operational learning:**
- Run in your van environment first (real constraints)
- Collect failure logs for 30 days
- Categorize emergent issues
- Update contract/schema based on findings

### Convert Unknown Knowns to Documentation
**Before v1.1 ships, extract:**
1. Design decision log (why JSON? why directory layout?)
2. Failure mode playbook (common errors + fixes)
3. Timing tuning guide (when to adjust tick_seconds)
4. Platform-specific notes (BSD vs Linux quirks)

This turns implicit knowledge into explicit onboarding material.

---

## Critical Path to Self-Defining Lattice

```
Known Knowns (working)
  ↓
+ Resolved Known Unknowns (board reader + compiler + reconcile)
  ↓
= Self-defining, self-healing lattice v1.1
  ↓
+ Instrumentation for Unknown Unknowns
  ↓
+ Documentation of Unknown Knowns
  ↓
= Production-ready lattice v1.2+
```

---

## The 20% That Closes the Loop

From your docs: "You already have 80% of it."

**The missing 20% is entirely in Known Unknowns territory:**
- Board reader: ~100 lines of JSON parsing + file walking
- Compiler: ~200 lines of translation logic (board → ConnectionLattice)
- Reconcile: ~150 lines of diff + idempotent POSIX ops

**Zero new conceptual machinery.** Just mechanical implementation of decisions you've already implicitly made through the schema design.

**The Unknown Unknowns won't block v1.1.** They'll surface during operational use and inform v1.2+.

---

## Conclusion

You're in an exceptionally strong position:
- **Known Knowns are solid**: runtime works, architecture is clean, POSIX substrate proven
- **Known Unknowns are tractable**: all answerable through straightforward implementation decisions
- **Unknown Knowns are accessible**: you have the domain expertise, just needs extraction
- **Unknown Unknowns are manageable**: instrumentation + iterative deployment will expose them safely

**The self-defining lattice is ready to build.** Start with the board reader, ship v1.1, instrument heavily, and let operational reality teach you what you don't yet know you don't know.