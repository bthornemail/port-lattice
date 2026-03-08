# Lattice Runtime Developer Guide

## Project Structure

```
lattice-runtime/
├── lattice                 # Main executable
├── runtime/                # Python package
│   ├── __init__.py        # Package exports
│   ├── board.py           # Board reader and validator
│   ├── compiler.py        # Board → ConnectionLattice compiler
│   ├── reconcile.py       # POSIX resource reconciliation
│   ├── health.py          # Health checking and healing
│   └── types.py           # Core data structures
├── examples/              # Example boards
├── docs/                  # Documentation
└── README.md
```

## Core Architecture

### Data Flow

```
Board (on disk)
  ↓ read_board()
Board (Python object)
  ↓ compile_lattice()
ConnectionLattice (in-memory)
  ↓ reconcile()
POSIX Resources (FIFOs, projections, processes)
  ↓ check_all()
Health State
  ↓ heal()
POSIX Resources (recreated if unhealthy)
```

### FIFO-First Model

- Ports are structural FIFOs.
- Transports are projections that attach to FIFO ports.
- Processes read/write FIFOs via env exports.

### Key Modules

#### board.py

- `read_board()`: Parse board.json + drop-ins → Board object
- `validate()`: Check constraints (duplicate names, invalid transports, etc)
- `run()`: Main control loop

#### compiler.py

- `compile_lattice()`: Pure transformation Board → ConnectionLattice
- No POSIX side effects
- Expands relative FIFO paths
- Converts transport specs into netcat args

#### reconcile.py

- `reconcile()`: Idempotent convergence to target lattice
- Creates FIFOs with `mkfifo`
- Starts/stops netcat transport projections
- Starts/stops processes

#### health.py

- `HealthChecker.check_all()`: Probe ports, transports, processes
- `HealthChecker.heal()`: Recreate unhealthy resources
- Respects restart_delay

#### types.py

- Dataclasses for Board, Port, Transport, Process
- ConnectionLattice and Runtime
- Transport handles (FIFO, Netcat)

## Development Workflow

### Setup

```bash
chmod +x lattice
mkdir -p test-board/state/sockets
cat > test-board/board.json <<EOF
{
  "node_id": "test",
  "socket_dir": "state/sockets",
  "ports": [],
  "transports": [],
  "procs": [],
  "health": {"tick_seconds": 2, "restart_delay": 1}
}
EOF
```

### Testing

```bash
./lattice validate examples/simple-board
./lattice run examples/simple-board --once
```

## Adding Features

### New Transport Kind

1. Add kind to `Transport` validation in `board.py`.
2. Add compiler logic in `compiler.py`.
3. Add reconciliation in `reconcile.py`.
4. Add health check + heal in `health.py`.
5. Update docs and examples.

### New Process Feature

1. Extend `Process` dataclass in `types.py`.
2. Update `_start_process()` in `reconcile.py`.
3. Update validation in `board.py`.
4. Update docs.

## Code Standards

- Type hints on all functions
- Dataclasses for structured data
- Pure functions in compiler
- No global state (pass Runtime explicitly)
- Log errors to stderr with context
