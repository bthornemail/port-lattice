# Lattice Runtime - Project Structure

## Overview

FIFO-first POSIX lattice runtime with netcat transport projections and
trace-sovereign observability.

## Status

Core features implemented:
- Board reader with drop-ins (`ports.d`, `transports.d`, `procs.d`)
- Board → ConnectionLattice compiler
- Idempotent reconciliation loop
- Self-probing health checker
- Automatic healing
- FIFO port materialization
- Netcat transport projections (TCP/UDP/SSL/Unix)
- Process management with dependencies
- Trace system with ULP bindings
- Test suite

## Directory Structure

```
lattice-runtime/
├── lattice                    # Main executable (Python)
├── runtime/                   # Core runtime package
│   ├── __init__.py
│   ├── board.py              # Board reader, validator, control loop
│   ├── compiler.py           # Board → ConnectionLattice compiler
│   ├── reconcile.py          # POSIX resource reconciliation
│   ├── health.py             # Health checking and healing
│   └── types.py              # Core data structures
├── examples/                  # Example boards
├── docs/                      # Documentation
├── README.md                  # User guide
├── DEVELOPERS.md             # Developer guide
├── TUTORIAL.md               # Step-by-step tutorial
├── CHANGELOG.md              # Version history
└── test-lattice.sh           # Test suite
```

## Key Concepts

- Ports are structural FIFOs.
- Transports attach to FIFO ports.
- Processes read/write FIFOs via env exports.
- Traces are append-only and resolve to ULP bindings.

## References

- `docs/board-schema.md`
- `docs/posix-lattice-contract.md`
- `TRACE-GUIDE.md`
