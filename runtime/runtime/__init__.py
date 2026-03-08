"""POSIX lattice runtime package."""

from .board import read_board, run, validate
from .compiler import compile_lattice
from .health import HealthChecker
from .reconcile import reconcile
from .trace import (
    TraceEmitter,
    compute_board_hash,
    emit_compile_trace,
    emit_heal_trace,
    emit_probe_trace,
    emit_reconcile_trace,
    emit_validation_error_trace,
    emit_warning_trace,
)
from .types import (
    Board,
    ConnectionLattice,
    FIFOTransport,
    HealthPolicy,
    KernelConfig,
    NetcatTransport,
    Peer,
    Port,
    Process,
    Runtime,
    Transport,
)

__all__ = [
    # Core functions
    "read_board",
    "validate",
    "run",
    "compile_lattice",
    "reconcile",
    # Trace functions
    "TraceEmitter",
    "compute_board_hash",
    "emit_compile_trace",
    "emit_heal_trace",
    "emit_probe_trace",
    "emit_reconcile_trace",
    "emit_validation_error_trace",
    "emit_warning_trace",
    # Types
    "Board",
    "ConnectionLattice",
    "FIFOTransport",
    "HealthChecker",
    "HealthPolicy",
    "KernelConfig",
    "NetcatTransport",
    "Peer",
    "Port",
    "Process",
    "Runtime",
    "Transport",
]
