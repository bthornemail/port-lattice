#!/usr/bin/env python3
"""Board reader, validator, and runtime controller for POSIX lattice."""

import json
import os
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .compiler import compile_lattice
from .health import HealthChecker
from .kernel_adapter import KernelGateError, run_kernel_gate
from .reconcile import reconcile
from .trace import (
    TraceEmitter,
    compute_board_hash,
    emit_compile_trace,
    emit_kernel_trace,
    emit_validation_error_trace,
    emit_warning_trace,
)
from .types import Board, ConnectionLattice, HealthPolicy, KernelConfig, Peer, Port, Process, Runtime, Transport


def _load_dropins(dir_path: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not dir_path.exists():
        return entries
    for entry in sorted(dir_path.glob("*.json")):
        with open(entry) as f:
            data = json.load(f)
        if isinstance(data, list):
            entries.extend(data)
        else:
            entries.append(data)
    return entries


def read_board(board_path: str) -> Board:
    """Read board directory and compile into Board structure.
    
    Args:
        board_path: Path to board directory
        
    Returns:
        Board object with all declarations loaded
        
    Raises:
        FileNotFoundError: If board_path doesn't exist
        ValueError: If board.json is malformed
    """
    board_dir = Path(board_path)
    if not board_dir.exists():
        raise FileNotFoundError(f"Board directory not found: {board_path}")
    
    # Read main board.json
    board_file = board_dir / "board.json"
    if not board_file.exists():
        raise FileNotFoundError(f"board.json not found in {board_path}")
    
    with open(board_file) as f:
        board_data = json.load(f)
    
    node_id = board_data.get("node_id", "local")
    socket_dir = board_data.get("socket_dir", "state/sockets")
    kernel_data = board_data.get("kernel")
    kernel_config = KernelConfig()
    if kernel_data:
        enabled = kernel_data.get("enabled", True)
        command = kernel_data.get("command")
        if isinstance(command, str):
            command = shlex.split(command)
        policy_path = kernel_data.get("policy")
        fail_open = kernel_data.get("fail_open", False)
        timeout_seconds = kernel_data.get("timeout_seconds", 10)
        kernel_config = KernelConfig(
            enabled=enabled,
            command=command,
            policy_path=policy_path,
            fail_open=fail_open,
            timeout_seconds=timeout_seconds
        )
    
    # Read drop-in peers
    peers: List[Peer] = []
    for peer_data in _load_dropins(board_dir / "peers.d"):
        peers.append(Peer(
            name=peer_data["name"],
            host=peer_data["host"],
            ssh_user=peer_data["ssh_user"],
            ssh_port=peer_data.get("ssh_port", 22),
            ssh_key=peer_data.get("ssh_key"),
            options=peer_data.get("options", [])
        ))
    
    # Add peers from board.json if present
    for peer_data in board_data.get("peers", []):
        peers.append(Peer(
            name=peer_data["name"],
            host=peer_data["host"],
            ssh_user=peer_data["ssh_user"],
            ssh_port=peer_data.get("ssh_port", 22),
            ssh_key=peer_data.get("ssh_key"),
            options=peer_data.get("options", [])
        ))
    
    # Read drop-in ports
    ports: List[Port] = []
    for port_data in _load_dropins(board_dir / "ports.d"):
        ports.append(Port(
            name=port_data["name"],
            direction=port_data.get("direction", "inout"),
            path=port_data.get("path"),
            probe=port_data.get("probe")
        ))
    
    # Add ports from board.json if present
    for port_data in board_data.get("ports", []):
        ports.append(Port(
            name=port_data["name"],
            direction=port_data.get("direction", "inout"),
            path=port_data.get("path"),
            probe=port_data.get("probe")
        ))

    # Read drop-in transports
    transports: List[Transport] = []
    for transport_data in _load_dropins(board_dir / "transports.d"):
        transports.append(Transport(
            name=transport_data["name"],
            kind=transport_data["kind"],
            attach=transport_data["attach"],
            spec=transport_data.get("spec", {})
        ))

    # Add transports from board.json if present
    for transport_data in board_data.get("transports", []):
        transports.append(Transport(
            name=transport_data["name"],
            kind=transport_data["kind"],
            attach=transport_data["attach"],
            spec=transport_data.get("spec", {})
        ))
    
    # Read drop-in processes
    procs: List[Process] = []
    for proc_data in _load_dropins(board_dir / "procs.d"):
        procs.append(Process(
            name=proc_data["name"],
            command=proc_data["command"],
            waits=proc_data.get("waits", []),
            fires=proc_data.get("fires", []),
            env=proc_data.get("env", {})
        ))
    
    # Add procs from board.json if present
    for proc_data in board_data.get("procs", []):
        procs.append(Process(
            name=proc_data["name"],
            command=proc_data["command"],
            waits=proc_data.get("waits", []),
            fires=proc_data.get("fires", []),
            env=proc_data.get("env", {})
        ))
    
    # Read health policy
    health_data = board_data.get("health", {})
    health_file = board_dir / "health.d" / "health.json"
    if health_file.exists():
        with open(health_file) as f:
            health_data = json.load(f)
    
    health = HealthPolicy(
        tick_seconds=health_data.get("tick_seconds", 2),
        restart_delay=health_data.get("restart_delay", 1),
        probe_grace_seconds=health_data.get("probe_grace_seconds", 2),
        failure_threshold=health_data.get("failure_threshold", 2),
    )
    
    return Board(
        node_id=node_id,
        board_path=str(board_dir),
        socket_dir=socket_dir,
        peers=peers,
        ports=ports,
        transports=transports,
        procs=procs,
        health=health,
        kernel=kernel_config
    )


def read_board_report(board_path: str) -> Tuple[Board, List[str]]:
    board = read_board(board_path)
    warnings: List[str] = []
    warnings.extend(_collision_warnings(board_path, "peers.d", "peers"))
    warnings.extend(_collision_warnings(board_path, "ports.d", "ports"))
    warnings.extend(_collision_warnings(board_path, "transports.d", "transports"))
    warnings.extend(_collision_warnings(board_path, "procs.d", "procs"))
    return board, warnings


def _collision_warnings(board_path: str, dropin_dir: str, section: str) -> List[str]:
    dir_path = Path(board_path) / dropin_dir
    if not dir_path.exists():
        return []
    seen: Dict[str, str] = {}
    warnings: List[str] = []
    for entry in sorted(dir_path.glob("*.json")):
        with open(entry) as f:
            data = json.load(f)
        items = data if isinstance(data, list) else [data]
        for item in items:
            name = item.get("name")
            if not name:
                continue
            if name in seen:
                warnings.append(f"{section} '{name}' overridden by {entry.name} (was {seen[name]})")
            seen[name] = entry.name
    return warnings


def generate_env(board: Board) -> None:
    env_dir = Path(board.board_path) / "env.d"
    env_dir.mkdir(parents=True, exist_ok=True)

    base_env = env_dir / "00-lattice.sh"
    with open(base_env, "w") as f:
        f.write("# Autogenerated. Source this file in your shell.\n")
        f.write(f"export LATTICE_BOARD='{board.board_path}'\n")
        f.write(f"export LATTICE_NODE_ID='{board.node_id}'\n")
        f.write(f"export LATTICE_SOCKET_DIR='{board.socket_dir}'\n")

    ports_env = env_dir / "10-ports.sh"
    with open(ports_env, "w") as f:
        f.write("# Autogenerated port exports.\n")
        for port in board.ports:
            key = f"LATTICE_PORT_{port.name.upper()}"
            in_path, out_path = _fifo_paths_for_port(board, port)
            value = in_path or out_path or ""
            f.write(f"export {key}='{value}'\n")
            f.write(f"export {key}_DIRECTION='{port.direction}'\n")
            if in_path:
                f.write(f"export {key}_IN='{in_path}'\n")
            if out_path:
                f.write(f"export {key}_OUT='{out_path}'\n")


def _fifo_paths_for_port(board: Board, port: Port) -> Tuple[Optional[str], Optional[str]]:
    base_path = port.path
    if base_path and not os.path.isabs(base_path):
        base_path = str(Path(board.board_path) / base_path)
    if not base_path:
        base_path = str(Path(board.board_path) / board.socket_dir / f"{port.name}.fifo")

    if port.direction == "inout":
        if base_path.endswith(".fifo"):
            base = base_path[:-5]
            return f"{base}.in.fifo", f"{base}.out.fifo"
        return f"{base_path}.in", f"{base_path}.out"
    if port.direction == "out":
        return None, base_path
    return base_path, None


def validate(board: Board) -> List[str]:
    """Validate board structure and constraints.
    
    Args:
        board: Board to validate
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check for duplicate names
    port_names = [p.name for p in board.ports]
    if len(port_names) != len(set(port_names)):
        duplicates = {name for name in port_names if port_names.count(name) > 1}
        errors.append(f"Duplicate port names: {duplicates}")
    
    proc_names = [p.name for p in board.procs]
    if len(proc_names) != len(set(proc_names)):
        duplicates = {name for name in proc_names if proc_names.count(name) > 1}
        errors.append(f"Duplicate process names: {duplicates}")
    
    peer_names = [p.name for p in board.peers]
    if len(peer_names) != len(set(peer_names)):
        duplicates = {name for name in peer_names if peer_names.count(name) > 1}
        errors.append(f"Duplicate peer names: {duplicates}")
    
    for port in board.ports:
        if port.direction not in {"in", "out", "inout"}:
            errors.append(f"Port {port.name}: direction must be in|out|inout")

    transport_names = [t.name for t in board.transports]
    if len(transport_names) != len(set(transport_names)):
        duplicates = {name for name in transport_names if transport_names.count(name) > 1}
        errors.append(f"Duplicate transport names: {duplicates}")
    port_name_set = set(port_names)
    if port_name_set.intersection(transport_names):
        collisions = sorted(port_name_set.intersection(transport_names))
        errors.append(f"Port/transport name collision: {collisions}")

    for transport in board.transports:
        if transport.attach not in port_name_set:
            errors.append(f"Transport {transport.name}: unknown port '{transport.attach}' in attach")
        if transport.kind != "netcat":
            errors.append(f"Transport {transport.name}: unsupported kind '{transport.kind}'")
            continue
        spec = transport.spec or {}
        protocol = spec.get("protocol")
        mode = spec.get("mode")
        if protocol not in {"tcp", "udp", "ssl", "unix"}:
            errors.append(f"Transport {transport.name}: invalid protocol '{protocol}'")
        if mode not in {"listen", "connect"}:
            errors.append(f"Transport {transport.name}: invalid mode '{mode}'")
        if protocol == "unix":
            if not spec.get("socket_path"):
                errors.append(f"Transport {transport.name}: unix protocol requires socket_path")
        else:
            if not spec.get("port"):
                errors.append(f"Transport {transport.name}: {protocol} requires port")
            if mode == "connect" and not spec.get("host"):
                errors.append(f"Transport {transport.name}: connect mode requires host")
    
    # Validate process dependencies
    for proc in board.procs:
        for wait in proc.waits:
            if wait not in port_name_set:
                errors.append(f"Process {proc.name}: unknown port '{wait}' in waits")
        for fire in proc.fires:
            if fire not in port_name_set:
                errors.append(f"Process {proc.name}: unknown port '{fire}' in fires")
    
    # Check for circular dependencies (simple check - doesn't catch complex cycles)
    proc_map = {p.name: p for p in board.procs}
    visited = set()
    
    def check_cycles(proc_name: str, path: Set[str]) -> None:
        if proc_name in path:
            errors.append(f"Circular dependency detected: {' -> '.join(path)} -> {proc_name}")
            return
        if proc_name in visited:
            return
        visited.add(proc_name)
        
        proc = proc_map.get(proc_name)
        if not proc:
            return
        
        new_path = path | {proc_name}
        for fire_port in proc.fires:
            # Find procs that wait on this port
            for other_proc in board.procs:
                if fire_port in other_proc.waits:
                    check_cycles(other_proc.name, new_path)
    
    for proc in board.procs:
        check_cycles(proc.name, set())

    if board.kernel.enabled:
        if not board.kernel.command:
            errors.append("Kernel gate enabled but no kernel.command configured")
        if board.kernel.policy_path:
            policy_path = board.kernel.policy_path
            if not os.path.isabs(policy_path):
                policy_path = os.path.join(board.board_path, policy_path)
            if not os.path.exists(policy_path):
                errors.append(f"Kernel policy not found: {policy_path}")

    return errors


def run(board_path: str, once: bool = False) -> None:
    """Run lattice control loop.
    
    Args:
        board_path: Path to board directory
        once: If True, run one tick and exit
    """
    print(f"[lattice] Starting runtime for board: {board_path}")
    
    # Read and validate board
    try:
        board, warnings = read_board_report(board_path)
    except Exception as e:
        print(f"[lattice] Error reading board: {e}", file=sys.stderr)
        sys.exit(1)
    
    errors = validate(board)
    if errors:
        print("[lattice] Board validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        
        # Emit validation error trace
        emitter = TraceEmitter(board_path)
        emit_validation_error_trace(emitter, errors)
        
        sys.exit(1)
    
    print(f"[lattice] Board loaded: {len(board.peers)} peers, {len(board.ports)} ports, {len(board.transports)} transports, {len(board.procs)} processes")
    
    # Initialize trace emitter
    emitter = TraceEmitter(board_path)
    if warnings:
        emit_warning_trace(emitter, warnings)
    
    # Initialize runtime state
    runtime = Runtime(
        board=board,
        lattice=None,
        processes={},
        transports={},
        health_state={}
    )
    
    # Initialize health checker
    health_checker = HealthChecker(board.health)
    
    # Signal handling
    shutdown_requested = False
    
    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        print(f"\n[lattice] Received signal {signum}, shutting down...")
        shutdown_requested = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    last_board: Optional[Board] = None
    last_board_hash: Optional[str] = None
    generation = 0

    # Main control loop
    tick = 0
    while not shutdown_requested:
        tick += 1
        print(f"\n[lattice] === Tick {tick} ===")
        
        try:
            # 1. Re-read board (allows live updates)
            board, warnings = read_board_report(board_path)
            runtime.board = board
            if warnings:
                emit_warning_trace(emitter, warnings)
            
            # Update board hash for trace attribution
            board_hash = compute_board_hash(board)
            emitter.set_board_hash(board_hash)
            if board_hash != last_board_hash:
                generation += 1
                last_board_hash = board_hash
            emitter.set_generation(generation)
            
            # Kernel gate (optional, pre-POSIX)
            if board.kernel.enabled:
                try:
                    decision = run_kernel_gate(board, last_board, board.kernel)
                    emit_kernel_trace(emitter, "blast_analyzed", decision.to_payload())
                    if decision.decision == "refuse":
                        emit_kernel_trace(emitter, "blast_refused", decision.to_payload())
                        print(f"[lattice] Kernel refused plan: {decision.reason}")
                        if once:
                            print("[lattice] Single tick refused by kernel, exiting")
                            break
                        time.sleep(board.health.tick_seconds)
                        continue
                    emit_kernel_trace(emitter, "blast_accepted", decision.to_payload())
                except KernelGateError as exc:
                    emit_kernel_trace(emitter, "blast_refused", {"reason": str(exc)})
                    print(f"[lattice] Kernel gate error: {exc}", file=sys.stderr)
                    if once:
                        print("[lattice] Single tick refused by kernel, exiting")
                        break
                    time.sleep(board.health.tick_seconds)
                    continue

            # 2. Compile to ConnectionLattice
            lattice = compile_lattice(board)
            old_lattice = runtime.lattice
            runtime.lattice = lattice

            # Emit env exports
            generate_env(board)
            
            # Emit compile trace
            emit_compile_trace(emitter, lattice)
            
            # 3. Reconcile (converge POSIX resources to match lattice)
            runtime = reconcile(runtime, old_lattice, lattice, emitter)
            
            # 4. Health check
            runtime = health_checker.check_all(runtime, emitter)
            
            # 5. Heal unhealthy resources
            runtime = health_checker.heal(runtime, emitter)

            last_board = board
            
        except Exception as e:
            print(f"[lattice] Error in control loop: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        if once:
            print("[lattice] Single tick complete, exiting")
            break
        
        # Sleep until next tick
        time.sleep(board.health.tick_seconds)
    
    # Cleanup
    print("[lattice] Shutting down...")
    
    # Stop all processes
    for proc_name, proc_handle in runtime.processes.items():
        print(f"[lattice] Stopping process: {proc_name}")
        try:
            proc_handle.terminate()
            proc_handle.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc_handle.kill()
        except Exception as e:
            print(f"[lattice] Error stopping {proc_name}: {e}")
    
    # Close all transports
    for transport_name, transport_handle in runtime.transports.items():
        print(f"[lattice] Closing transport: {transport_name}")
        try:
            if hasattr(transport_handle, 'process') and transport_handle.process:
                transport_handle.process.terminate()
                try:
                    transport_handle.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    transport_handle.process.kill()
                    transport_handle.process.wait(timeout=5)
            elif hasattr(transport_handle, 'close'):
                transport_handle.close()
            elif hasattr(transport_handle, 'terminate'):
                transport_handle.terminate()
        except Exception as e:
            print(f"[lattice] Error closing {transport_name}: {e}")
    
    print("[lattice] Shutdown complete")


if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) > 1:
        board = read_board(sys.argv[1])
        errors = validate(board)
        if errors:
            print("Validation errors:")
            for err in errors:
                print(f"  - {err}")
        else:
            print("Board is valid")
            print(f"  Peers: {len(board.peers)}")
            print(f"  Ports: {len(board.ports)}")
            print(f"  Transports: {len(board.transports)}")
            print(f"  Procs: {len(board.procs)}")
