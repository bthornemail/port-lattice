#!/usr/bin/env python3
"""Type definitions for POSIX lattice runtime."""

from dataclasses import dataclass, field
from subprocess import Popen
from typing import Any, Dict, List, Optional


@dataclass
class HealthPolicy:
    """Health check and restart policy."""
    tick_seconds: int = 2
    restart_delay: int = 1
    probe_grace_seconds: int = 2
    failure_threshold: int = 2


@dataclass
class Peer:
    """Remote peer definition for SSH tunnels."""
    name: str
    host: str
    ssh_user: str
    ssh_port: int = 22
    ssh_key: Optional[str] = None
    options: List[str] = field(default_factory=list)


@dataclass
class KernelConfig:
    """Kernel gate configuration."""
    enabled: bool = False
    command: Optional[List[str]] = None
    policy_path: Optional[str] = None
    fail_open: bool = False
    timeout_seconds: int = 10


@dataclass
class Port:
    """Port definition (FIFO-first structural endpoint)."""
    name: str
    direction: str = "inout"  # "in", "out", "inout"
    path: Optional[str] = None
    probe: Optional[Dict[str, Any]] = None


@dataclass
class Transport:
    """Transport projection attached to a FIFO port."""
    name: str
    kind: str  # "netcat"
    attach: str  # Port name
    spec: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Process:
    """Process specification."""
    name: str
    command: str
    waits: List[str] = field(default_factory=list)  # Port names to wait for
    fires: List[str] = field(default_factory=list)  # Port names this writes to
    env: Dict[str, str] = field(default_factory=dict)  # Additional env vars


@dataclass
class Board:
    """Board: authoritative lattice definition."""
    node_id: str
    board_path: str
    socket_dir: str
    peers: List[Peer]
    ports: List[Port]
    transports: List[Transport]
    procs: List[Process]
    health: HealthPolicy
    kernel: KernelConfig = field(default_factory=KernelConfig)


@dataclass
class FIFOTransport:
    """FIFO transport handle."""
    name: str
    path: str
    created: bool = False


@dataclass
class NetcatTransport:
    """Netcat transport handle."""
    name: str
    args: List[str]
    attach: str
    spec: Dict[str, Any] = field(default_factory=dict)
    process: Optional[Popen] = None
    fifo_in_path: Optional[str] = None
    fifo_out_path: Optional[str] = None


@dataclass
class ConnectionLattice:
    """Compiled in-memory lattice representation."""
    node_id: str
    socket_dir: str
    fifos: List[FIFOTransport] = field(default_factory=list)
    netcat_transports: List[NetcatTransport] = field(default_factory=list)
    processes: List[Process] = field(default_factory=list)
    
    def get_port_path(self, port_name: str, role: str = "wait") -> Optional[str]:
        """Get filesystem path for a named port and role."""
        suffix = ".in" if role == "wait" else ".out"
        for fifo in self.fifos:
            if fifo.name == f"{port_name}{suffix}":
                return fifo.path
        for fifo in self.fifos:
            if fifo.name == port_name:
                return fifo.path
        return None


@dataclass
class Runtime:
    """Runtime state."""
    board: Board
    lattice: Optional[ConnectionLattice]
    processes: Dict[str, Popen]  # name -> Popen handle
    transports: Dict[str, Any]  # name -> transport handle
    health_state: Dict[str, str]  # name -> "healthy" | "unhealthy" | "unknown"
