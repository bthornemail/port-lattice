# Changelog

All notable changes to the Lattice Runtime will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-25

### Added
- **Trace System**: Complete immutable trace emission with blackboard pattern
- **ULP Bindings**: Every event represented as polynomial over atoms
- **Coxeter Structure**: Chain complex export for geometric analysis
- **trace-resolve**: Command-line tool for trace validation and analysis
- TraceEmitter class for append-only event logging
- Trace events: compile, reconcile, probe, heal, validate_error, warnings
- ULP export: `--export-ulp` generates polynomial bindings
- Coxeter export: `--export-coxeter` extracts chain complex
- Verbose analysis mode with health statistics
- Board hash tracking for event attribution
- Content-addressable event IDs (SHA256)
- Comprehensive trace documentation (TRACE-GUIDE.md)
- Trace schema documentation (docs/trace-schema.md)

### Changed
- Runtime now emits all actions to state/traces/trace.log
- Health checker emits probe events with status
- Reconciler emits create/destroy events
- Compiler emits compilation events

## [1.0.0] - 2026-01-25

### Added
- Initial release of self-defining, self-healing POSIX lattice runtime
- Board reader with JSON parsing and drop-in file support
- Compiler: Board → ConnectionLattice transformation
- Reconciliation engine for idempotent POSIX resource convergence
- Health checker with self-probing capabilities
- Automatic healing of unhealthy resources
- Support for FIFO transports
- Support for SSH tunnel transports
- Support for Unix domain socket transports
- Process management with dependency tracking
- Environment variable expansion (LATTICE_NODE_ID, LATTICE_PORT_*)
- Board validation with constraint checking
- Duplicate name detection
- Circular dependency detection
- Single-tick mode for testing (--once flag)
- Comprehensive documentation (README, DEVELOPERS, TUTORIAL)
- Example boards (simple-board, ssh-tunnel-board)
- Test suite (test-lattice.sh)
- Makefile for build/test/install
- Board schema documentation
- POSIX lattice runtime contract

### Features
- **Self-Defining**: Entire network environment derived from board files
- **Self-Healing**: Automatic detection and recreation of failed resources
- **POSIX-Native**: All resources observable with standard tools (mkfifo, ps, lsof, ssh)
- **Deterministic**: Same board produces same startup sequence
- **Idempotent**: Safe to run reconcile loop repeatedly
- **Live Updates**: Board changes picked up on next tick without restart

### Known Limitations
- No incremental compilation (full recompile each tick)
- No dynamic peer discovery (static declarations only)
- No tunnel multiplexing (one SSH connection per tunnel)
- No built-in metrics export
- Basic health probes (process liveness only, no TCP connection tests)

## [Unreleased]

### Added
- FIFO-first port model (ports are structural FIFOs only)
- Transport projections via `transports` (netcat TCP/UDP/SSL/Unix)
- Netcat example board (examples/netcat-board)
- Optional kernel gate via external `lattice-kernel` command

### Changed
- **Breaking**: port `type` removed; transport declarations moved to `transports`
- Reconcile actions now emit structural names (`port_materialized`, `transport_attached`)
- Board hashing now includes transports for trace attribution

### Planned
- Incremental compilation for large boards
- TCP connection health probes
- Tunnel multiplexing for efficiency
- Metrics export (Prometheus format)
- Process log file management
- Graceful shutdown improvements
- inotify-based board file watching
- PID file management enhancements
