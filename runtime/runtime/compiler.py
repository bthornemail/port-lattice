#!/usr/bin/env python3
"""Compiler: Board -> ConnectionLattice transformation."""

import os
from typing import Dict, List, Optional

from .types import (
    Board,
    ConnectionLattice,
    FIFOTransport,
    NetcatTransport,
    Port,
    Process,
    Transport,
)


def compile_lattice(board: Board) -> ConnectionLattice:
    """Compile board definition into ConnectionLattice.
    
    This is a pure transformation that converts declarative board
    into runtime data structures. No POSIX resources are created here.
    
    Args:
        board: Board definition
        
    Returns:
        ConnectionLattice ready for reconciliation
    """
    lattice = ConnectionLattice(
        node_id=board.node_id,
        socket_dir=board.socket_dir
    )
    
    fifo_map: Dict[str, Dict[str, str]] = {}
    port_map = {p.name: p for p in board.ports}
    
    # Compile ports into FIFOs first (FIFO-first projection model)
    for port in board.ports:
        fifo_paths = _compile_fifo_paths(board, port)
        fifo_map[port.name] = fifo_paths
        for fifo_name, fifo_path in fifo_paths.items():
            lattice.fifos.append(FIFOTransport(name=fifo_name, path=fifo_path, created=False))

    # Compile transport projections
    for transport in board.transports:
        if transport.kind == "netcat":
            fifo_paths = fifo_map.get(transport.attach, {})
            port = port_map.get(transport.attach)
            lattice.netcat_transports.append(_compile_netcat(board, transport, port, fifo_paths))
    
    # Copy processes (with env variable expansion deferred to reconcile)
    lattice.processes = board.procs.copy()
    
    return lattice


def _compile_fifo_paths(board: Board, port: Port) -> Dict[str, str]:
    """Compile FIFO paths for a port (supports duplex)."""
    if not port.path:
        base_path = os.path.join(board.board_path, board.socket_dir, f"{port.name}.fifo")
    else:
        base_path = port.path
        if not os.path.isabs(base_path):
            base_path = os.path.join(board.board_path, base_path)

    if port.direction == "inout":
        if base_path.endswith(".fifo"):
            base = base_path[:-5]
            return {
                f"{port.name}.in": f"{base}.in.fifo",
                f"{port.name}.out": f"{base}.out.fifo",
            }
        return {
            f"{port.name}.in": f"{base_path}.in",
            f"{port.name}.out": f"{base_path}.out",
        }
    if port.direction == "out":
        return {f"{port.name}.out": base_path}
    return {f"{port.name}.in": base_path}


def _compile_netcat(
    board: Board,
    transport: Transport,
    port: Optional[Port],
    fifo_paths: Dict[str, str],
) -> NetcatTransport:
    """Compile netcat transport projection."""
    spec = transport.spec or {}
    protocol = spec.get("protocol")
    mode = spec.get("mode")
    args: List[str] = []
    if protocol == "udp":
        args.append("-u")
    elif protocol == "ssl":
        args.append("-S")
    elif protocol == "unix":
        args.append("-U")

    if mode == "listen":
        if protocol == "unix":
            socket_path = spec.get("socket_path")
            args.extend(["-l", "-L", str(socket_path)])
        else:
            port_value = spec.get("port")
            args.extend(["-l", "-p", str(port_value)])
        if spec.get("keep_open"):
            args.append("-k")
    else:
        if protocol == "unix":
            socket_path = spec.get("socket_path")
            args.extend(["-L", str(socket_path)])
        else:
            host = spec.get("host", "127.0.0.1")
            port_value = spec.get("port")
            args.extend([host, str(port_value)])

    if protocol == "udp" and spec.get("udp_wait") is not None:
        args.append(f"--udp-wait={spec.get('udp_wait')}")

    exec_cmd = spec.get("exec")
    if exec_cmd:
        args = ["-e", exec_cmd] + args

    fifo_in_path = None
    fifo_out_path = None
    if port and port.direction:
        if port.direction == "in":
            fifo_out_path = fifo_paths.get(f"{port.name}.in")
        elif port.direction == "out":
            fifo_in_path = fifo_paths.get(f"{port.name}.out")
        else:
            fifo_in_path = fifo_paths.get(f"{port.name}.out")
            fifo_out_path = fifo_paths.get(f"{port.name}.in")

    return NetcatTransport(
        name=transport.name,
        args=args,
        attach=transport.attach,
        spec=spec,
        process=None,
        fifo_in_path=fifo_in_path,
        fifo_out_path=fifo_out_path
    )
