#!/usr/bin/env python3
"""Self-defining lattice runtime: board compiler + reconciler."""

from __future__ import annotations

import json
import os
import signal
import socket
import ssl
import stat
import subprocess
import time
from hashlib import sha256
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from trace_schema import build_event


@dataclass
class Peer:
    name: str
    host: str
    ssh_user: Optional[str] = None
    ssh_port: int = 22
    ssh_key: Optional[str] = None
    options: List[str] = field(default_factory=list)


@dataclass
class Port:
    name: str
    type: str
    path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    peer: Optional[str] = None
    local_port: Optional[int] = None
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    probe_type: Optional[str] = None
    probe_host: Optional[str] = None
    probe_port: Optional[int] = None
    probe_path: Optional[str] = None


@dataclass
class ProcSpec:
    name: str
    command: List[str]
    cwd: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    waits: List[str] = field(default_factory=list)
    fires: List[str] = field(default_factory=list)


@dataclass
class HealthPolicy:
    tick_seconds: int = 2
    restart_delay: int = 1


@dataclass
class Board:
    node_id: str
    socket_dir: str
    peers: Dict[str, Peer] = field(default_factory=dict)
    ports: Dict[str, Port] = field(default_factory=dict)
    procs: Dict[str, ProcSpec] = field(default_factory=dict)
    health: HealthPolicy = field(default_factory=HealthPolicy)


@dataclass
class ConnectionLattice:
    peers: Dict[str, Peer]
    ports: Dict[str, Port]
    procs: Dict[str, ProcSpec]


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_dropins(dir_path: str) -> List[dict]:
    if not os.path.isdir(dir_path):
        return []
    entries: List[dict] = []
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".json"):
            continue
        data = _read_json(os.path.join(dir_path, name))
        if isinstance(data, list):
            entries.extend(data)
        else:
            entries.append(data)
    return entries


def read_board(board_dir: str) -> Board:
    board_path = os.path.join(board_dir, "board.json")
    base = _read_json(board_path) if os.path.exists(board_path) else {}

    node_id = base.get("node_id") or socket.gethostname()
    socket_dir = base.get("socket_dir") or os.path.join(board_dir, "state", "sockets")

    peers_list = base.get("peers", []) + _load_dropins(os.path.join(board_dir, "peers.d"))
    ports_list = base.get("ports", []) + _load_dropins(os.path.join(board_dir, "ports.d"))
    procs_list = base.get("procs", []) + _load_dropins(os.path.join(board_dir, "procs.d"))

    health = base.get("health")
    health_path = os.path.join(board_dir, "health.d", "health.json")
    if not health and os.path.exists(health_path):
        health = _read_json(health_path)

    peers = _merge_peers(peers_list)
    ports = _merge_ports(ports_list)
    procs = _merge_procs(procs_list)

    health_policy = HealthPolicy(
        tick_seconds=int((health or {}).get("tick_seconds", 2)),
        restart_delay=int((health or {}).get("restart_delay", 1)),
    )

    return Board(
        node_id=node_id,
        socket_dir=socket_dir,
        peers=peers,
        ports=ports,
        procs=procs,
        health=health_policy,
    )


def read_board_report(board_dir: str) -> Tuple[Board, List[str]]:
    board = read_board(board_dir)
    warnings: List[str] = []
    warnings.extend(_collision_warnings(board_dir, "peers.d", "peers"))
    warnings.extend(_collision_warnings(board_dir, "ports.d", "ports"))
    warnings.extend(_collision_warnings(board_dir, "procs.d", "procs"))
    return board, warnings


def _collision_warnings(board_dir: str, dropin_dir: str, section: str) -> List[str]:
    dir_path = os.path.join(board_dir, dropin_dir)
    if not os.path.isdir(dir_path):
        return []
    seen: Dict[str, str] = {}
    warnings: List[str] = []
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".json"):
            continue
        data = _read_json(os.path.join(dir_path, name))
        items = data if isinstance(data, list) else [data]
        for item in items:
            item_name = item.get("name")
            if not item_name:
                continue
            if item_name in seen:
                warnings.append(
                    f"{section} '{item_name}' overridden by {name} (was {seen[item_name]})"
                )
            seen[item_name] = name
    return warnings


def _merge_peers(peers_list: List[dict]) -> Dict[str, Peer]:
    peers: Dict[str, Peer] = {}
    for peer in peers_list:
        peers[peer["name"]] = Peer(
            name=peer["name"],
            host=peer["host"],
            ssh_user=peer.get("ssh_user"),
            ssh_port=int(peer.get("ssh_port", 22)),
            ssh_key=peer.get("ssh_key"),
            options=peer.get("options", []),
        )
    return peers


def _merge_ports(ports_list: List[dict]) -> Dict[str, Port]:
    ports: Dict[str, Port] = {}
    for port in ports_list:
        probe = port.get("probe", {})
        ports[port["name"]] = Port(
            name=port["name"],
            type=port["type"],
            path=port.get("path"),
            host=port.get("host"),
            port=port.get("port"),
            peer=port.get("peer"),
            local_port=port.get("local_port"),
            remote_host=port.get("remote_host"),
            remote_port=port.get("remote_port"),
            probe_type=probe.get("type"),
            probe_host=probe.get("host"),
            probe_port=probe.get("port"),
            probe_path=probe.get("path"),
        )
    return ports


def _merge_procs(procs_list: List[dict]) -> Dict[str, ProcSpec]:
    procs: Dict[str, ProcSpec] = {}
    for proc in procs_list:
        command = proc.get("command")
        if isinstance(command, str):
            command = ["sh", "-c", command]
        procs[proc["name"]] = ProcSpec(
            name=proc["name"],
            command=command,
            cwd=proc.get("cwd"),
            env=proc.get("env", {}),
            waits=proc.get("waits", []),
            fires=proc.get("fires", []),
        )
    return procs


def compile_board(board: Board) -> ConnectionLattice:
    return ConnectionLattice(peers=board.peers, ports=board.ports, procs=board.procs)


def generate_env(board_dir: str, board: Board) -> None:
    env_dir = os.path.join(board_dir, "env.d")
    os.makedirs(env_dir, exist_ok=True)

    base_env_path = os.path.join(env_dir, "00-lattice.sh")
    with open(base_env_path, "w", encoding="utf-8") as f:
        f.write("# Autogenerated. Source this file in your shell.\n")
        f.write(f"export LATTICE_BOARD='{board_dir}'\n")
        f.write(f"export LATTICE_NODE_ID='{board.node_id}'\n")
        f.write(f"export LATTICE_SOCKET_DIR='{board.socket_dir}'\n")
        for peer in board.peers.values():
            key = f"LATTICE_PEER_{peer.name.upper()}"
            user = f"{peer.ssh_user}@" if peer.ssh_user else ""
            f.write(f"export {key}='{user}{peer.host}:{peer.ssh_port}'\n")

    ports_env_path = os.path.join(env_dir, "10-ports.sh")
    with open(ports_env_path, "w", encoding="utf-8") as f:
        f.write("# Autogenerated port exports.\n")
        for port in board.ports.values():
            key = f"LATTICE_PORT_{port.name.upper()}"
            value = port.path
            if not value and port.host and port.port:
                value = f"{port.host}:{port.port}"
            if not value and port.local_port:
                value = str(port.local_port)
            if value:
                f.write(f"export {key}='{value}'\n")
                f.write(f"export {key}_TYPE='{port.type}'\n")


def ensure_fifo(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return
    os.mkfifo(path)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid(pid_file: str) -> Optional[int]:
    try:
        with open(pid_file, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _write_pid(pid_file: str, pid: int) -> None:
    with open(pid_file, "w", encoding="utf-8") as f:
        f.write(str(pid))


def _stop_pid(pid_file: str) -> None:
    pid = _read_pid(pid_file)
    if not pid:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        os.remove(pid_file)
    except OSError:
        pass


def ensure_ssh_forward(
    name: str,
    port: Port,
    peer: Peer,
    state_dir: str,
    restart_delay: int,
) -> None:
    pid_file = os.path.join(state_dir, f"ssh_{name}.pid")
    pid = _read_pid(pid_file)
    if pid and _pid_alive(pid):
        return

    local_port = port.local_port or port.port
    if not local_port:
        raise ValueError(f"SSH port '{name}' missing local_port")

    remote_host = port.remote_host or "localhost"
    remote_port = port.remote_port or port.port
    if not remote_port:
        raise ValueError(f"SSH port '{name}' missing remote_port")

    target = f"{peer.host}"
    if peer.ssh_user:
        target = f"{peer.ssh_user}@{peer.host}"

    cmd = [
        "ssh",
        "-N",
        "-L",
        f"{local_port}:{remote_host}:{remote_port}",
        "-p",
        str(peer.ssh_port),
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
    ]
    if peer.ssh_key:
        cmd.extend(["-i", peer.ssh_key])
    for opt in peer.options:
        cmd.extend(["-o", opt])
    cmd.append(target)

    proc = subprocess.Popen(cmd)
    _write_pid(pid_file, proc.pid)
    time.sleep(restart_delay)


def ensure_proc(
    proc: ProcSpec,
    board: Board,
    state_dir: str,
    restart_delay: int,
) -> None:
    pid_file = os.path.join(state_dir, f"proc_{proc.name}.pid")
    pid = _read_pid(pid_file)
    if pid and _pid_alive(pid):
        return

    env = os.environ.copy()
    env.update(proc.env)
    env["LATTICE_BOARD"] = board.node_id
    env["LATTICE_SOCKET_DIR"] = board.socket_dir
    for port in board.ports.values():
        key = f"LATTICE_PORT_{port.name.upper()}"
        value = port.path
        if not value and port.host and port.port:
            value = f"{port.host}:{port.port}"
        if not value and port.local_port:
            value = str(port.local_port)
        if value:
            env[key] = value

    proc_obj = subprocess.Popen(proc.command, cwd=proc.cwd, env=env)
    _write_pid(pid_file, proc_obj.pid)
    time.sleep(restart_delay)


def reconcile(board_dir: str, board: Board, lattice: ConnectionLattice) -> None:
    state_dir = os.path.join(board_dir, "state")
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(board.socket_dir, exist_ok=True)

    for port in lattice.ports.values():
        if port.type == "fifo":
            if not port.path:
                raise ValueError(f"FIFO port '{port.name}' missing path")
            ensure_fifo(port.path)

    for name, port in lattice.ports.items():
        if port.type == "ssh_forward":
            if not port.peer:
                raise ValueError(f"SSH port '{name}' missing peer")
            peer = lattice.peers.get(port.peer)
            if not peer:
                raise ValueError(f"SSH port '{name}' references unknown peer '{port.peer}'")
            ensure_ssh_forward(name, port, peer, state_dir, board.health.restart_delay)

    for proc in lattice.procs.values():
        ensure_proc(proc, board, state_dir, board.health.restart_delay)

    desired_proc_pids = {f"proc_{name}.pid" for name in lattice.procs}
    desired_ssh_pids = {f"ssh_{name}.pid" for name, p in lattice.ports.items() if p.type == "ssh_forward"}
    for name in os.listdir(state_dir):
        if name.startswith("proc_") and name.endswith(".pid"):
            if name not in desired_proc_pids:
                _stop_pid(os.path.join(state_dir, name))
        if name.startswith("ssh_") and name.endswith(".pid"):
            if name not in desired_ssh_pids:
                _stop_pid(os.path.join(state_dir, name))


def validate(board: Board) -> List[str]:
    errors: List[str] = []
    for proc in board.procs.values():
        for port in proc.waits + proc.fires:
            if port not in board.ports:
                errors.append(f"proc {proc.name} references missing port {port}")
    for port in board.ports.values():
        if port.type == "ssh_forward" and port.peer and port.peer not in board.peers:
            errors.append(f"port {port.name} references missing peer {port.peer}")
    return errors


def _now_ts() -> int:
    return int(time.time())


def _health_path(state_dir: str) -> str:
    return os.path.join(state_dir, "health.json")


def load_health(state_dir: str) -> dict:
    path = _health_path(state_dir)
    if not os.path.exists(path):
        return {"updated_at": _now_ts(), "resources": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_health(state_dir: str, health: dict) -> None:
    health["updated_at"] = _now_ts()
    with open(_health_path(state_dir), "w", encoding="utf-8") as f:
        json.dump(health, f, indent=2)


def _probe_tcp(host: str, port: int, timeout: int) -> Tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except OSError as exc:
        return False, str(exc)


def _probe_udp(host: str, port: int, timeout: int) -> Tuple[bool, str]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(b"", (host, port))
        sock.close()
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _probe_unix(path: str, timeout: int) -> Tuple[bool, str]:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(path)
        sock.close()
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _probe_ssl(host: str, port: int, timeout: int) -> Tuple[bool, str]:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw_sock:
            with context.wrap_socket(raw_sock, server_hostname=host):
                return True, ""
    except OSError as exc:
        return False, str(exc)


def probe_resources(
    board: Board,
    lattice: ConnectionLattice,
    state_dir: str,
    timeout: int = 2,
) -> Tuple[dict, List[str]]:
    health = load_health(state_dir)
    resources = health.get("resources", {})
    unhealthy: List[str] = []

    for name, port in lattice.ports.items():
        key = f"port:{name}"
        status = {"status": "unknown", "last_error": "", "last_checked": _now_ts()}
        probe_type = port.probe_type or port.type
        probe_host = port.probe_host or port.host or "localhost"
        probe_port = port.probe_port or port.port
        probe_path = port.probe_path or port.path
        if probe_type == "fifo":
            if port.path and os.path.exists(port.path) and stat.S_ISFIFO(os.stat(port.path).st_mode):
                status["status"] = "healthy"
            else:
                status["status"] = "unhealthy"
                status["last_error"] = "fifo missing or invalid"
        elif probe_type == "ssh_forward":
            pid_file = os.path.join(state_dir, f"ssh_{name}.pid")
            pid = _read_pid(pid_file)
            if pid and _pid_alive(pid):
                status["status"] = "healthy"
            else:
                status["status"] = "unhealthy"
                status["last_error"] = "ssh forward not running"
        elif probe_type in {"tcp", "udp", "unix", "ssl"}:
            if probe_type == "unix" and probe_path:
                ok, err = _probe_unix(probe_path, timeout)
            elif probe_type == "udp" and probe_port:
                ok, err = _probe_udp(probe_host, probe_port, timeout)
            elif probe_type == "ssl" and probe_port:
                ok, err = _probe_ssl(probe_host, probe_port, timeout)
            elif probe_port:
                ok, err = _probe_tcp(probe_host, probe_port, timeout)
            else:
                ok, err = False, "missing host/port/path"
            status["status"] = "healthy" if ok else "unhealthy"
            status["last_error"] = "" if ok else err
        else:
            status["status"] = "unknown"
            status["last_error"] = "unsupported port type"

        resources[key] = status
        if status["status"] == "unhealthy":
            unhealthy.append(key)

    for name in lattice.procs:
        key = f"proc:{name}"
        pid_file = os.path.join(state_dir, f"proc_{name}.pid")
        pid = _read_pid(pid_file)
        status = {"status": "healthy", "last_error": "", "last_checked": _now_ts()}
        if not pid or not _pid_alive(pid):
            status["status"] = "unhealthy"
            status["last_error"] = "process not running"
        resources[key] = status
        if status["status"] == "unhealthy":
            unhealthy.append(key)

    health["resources"] = resources
    return health, unhealthy


def heal_unhealthy(
    board: Board,
    lattice: ConnectionLattice,
    state_dir: str,
    unhealthy: List[str],
) -> None:
    for key in unhealthy:
        if key.startswith("proc:"):
            name = key.split(":", 1)[1]
            _stop_pid(os.path.join(state_dir, f"proc_{name}.pid"))
            proc = lattice.procs.get(name)
            if proc:
                ensure_proc(proc, board, state_dir, board.health.restart_delay)
        elif key.startswith("port:"):
            name = key.split(":", 1)[1]
            port = lattice.ports.get(name)
            if not port:
                continue
            if port.type == "fifo" and port.path:
                if os.path.exists(port.path) and not stat.S_ISFIFO(os.stat(port.path).st_mode):
                    os.remove(port.path)
                ensure_fifo(port.path)
            elif port.type == "ssh_forward":
                _stop_pid(os.path.join(state_dir, f"ssh_{name}.pid"))
                peer = lattice.peers.get(port.peer or "")
                if peer:
                    ensure_ssh_forward(name, port, peer, state_dir, board.health.restart_delay)


def emit_trace(state_dir: str, event_type: str, payload: dict, board_hash: Optional[str] = None) -> None:
    traces_dir = os.path.join(state_dir, "traces")
    os.makedirs(traces_dir, exist_ok=True)
    event = build_event(event_type, payload, board_hash=board_hash)
    trace_path = os.path.join(traces_dir, "trace.log")
    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def board_to_dict(board: Board) -> dict:
    return {
        "node_id": board.node_id,
        "socket_dir": board.socket_dir,
        "peers": {name: peer.__dict__ for name, peer in board.peers.items()},
        "ports": {name: port.__dict__ for name, port in board.ports.items()},
        "procs": {name: proc.__dict__ for name, proc in board.procs.items()},
        "health": board.health.__dict__,
    }


def run(board_dir: str, once: bool = False) -> None:
    while True:
        board, warnings = read_board_report(board_dir)
        lattice = compile_board(board)
        generate_env(board_dir, board)
        errors = validate(board)
        if errors:
            for err in errors:
                print(f"Validation error: {err}")
            emit_trace(
                os.path.join(board_dir, "state"),
                "validate_error",
                {"errors": errors},
            )
        else:
            reconcile(board_dir, board, lattice)
            state_dir = os.path.join(board_dir, "state")
            board_dict = board_to_dict(board)
            board_hash = sha256(json.dumps(board_dict, sort_keys=True).encode()).hexdigest()
            emit_trace(state_dir, "compile", {"board_hash": board_hash}, board_hash=board_hash)
            if warnings:
                emit_trace(state_dir, "warnings", {"warnings": warnings}, board_hash=board_hash)
            emit_trace(state_dir, "reconcile", {"board_hash": board_hash}, board_hash=board_hash)
            health, unhealthy = probe_resources(board, lattice, state_dir)
            emit_trace(
                state_dir,
                "probe",
                {"board_hash": board_hash, "unhealthy": unhealthy},
                board_hash=board_hash,
            )
            if unhealthy:
                heal_unhealthy(board, lattice, state_dir, unhealthy)
                emit_trace(
                    state_dir,
                    "heal",
                    {"board_hash": board_hash, "unhealthy": unhealthy},
                    board_hash=board_hash,
                )
            save_health(state_dir, health)
        if once:
            break
        time.sleep(board.health.tick_seconds)
