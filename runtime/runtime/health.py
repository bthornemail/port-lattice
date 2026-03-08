#!/usr/bin/env python3
"""Health checking and healing for lattice transports and processes."""

import json
import os
import socket
import ssl
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Tuple

from .types import FIFOTransport, HealthPolicy, NetcatTransport, Runtime


class HealthChecker:
    """Self-probing, self-healing health checker."""

    def __init__(self, policy: HealthPolicy):
        self.policy = policy
        self.last_heal_time: Dict[str, float] = {}
        self.start_times: Dict[str, float] = {}
        self.failure_counts: Dict[str, int] = {}
        self.last_pids: Dict[str, int] = {}
        self.last_accept_ts: Dict[str, float] = {}
        self.last_probe_details: Dict[str, Dict[str, Any]] = {}

    def check_all(self, runtime: Runtime, emitter: Any) -> Runtime:
        """Check health of all transports and processes.

        Updates runtime.health_state with current status.

        Args:
            runtime: Current runtime state
            emitter: Trace emitter

        Returns:
            Updated runtime with health_state populated
        """
        from .trace import emit_probe_trace

        print("[health] Checking all resources")
        self.last_probe_details = {}

        # Check transports (projections)
        for name, transport in runtime.transports.items():
            if isinstance(transport, NetcatTransport):
                status, details = self._check_netcat(name, transport)
                runtime.health_state[name] = status
                if details:
                    self.last_probe_details[name] = details
                emit_probe_trace(emitter, name, status, details)

        # Check ports with probe policies
        for port in runtime.board.ports:
            status = self._check_port(runtime, port)
            runtime.health_state[port.name] = status
            emit_probe_trace(emitter, port.name, status)

        # Check processes
        for name, proc in runtime.processes.items():
            status = self._check_process(proc)
            runtime.health_state[name] = status
            emit_probe_trace(emitter, name, status)

        # Report health summary
        healthy = sum(1 for s in runtime.health_state.values() if s == "healthy")
        unhealthy = sum(1 for s in runtime.health_state.values() if s == "unhealthy")
        unknown = sum(1 for s in runtime.health_state.values() if s == "unknown")
        warming = sum(1 for s in runtime.health_state.values() if s == "warming")

        print(f"[health] Status: {healthy} healthy, {unhealthy} unhealthy, {warming} warming, {unknown} unknown")

        self._write_health(runtime)

        return runtime

    def _write_health(self, runtime: Runtime) -> None:
        state_dir = os.path.join(runtime.board.board_path, "state")
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, "health.json")
        payload = {
            "updated_at": time.time(),
            "resources": runtime.health_state,
            "details": self.last_probe_details,
        }
        try:
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"[health] Error writing health.json: {e}", file=sys.stderr)

    def _check_process(self, proc: subprocess.Popen) -> str:
        """Check process health.

        Args:
            proc: Process to check

        Returns:
            "healthy", "unhealthy", or "unknown"
        """
        retcode = proc.poll()
        if retcode is not None:
            return "unhealthy"

        return "healthy"

    def _check_netcat(self, name: str, transport: NetcatTransport) -> Tuple[str, Optional[Dict[str, Any]]]:
        pid = transport.process.pid if transport.process else None
        if pid is None:
            return self._register_failure(name), None

        last_pid = self.last_pids.get(name)
        if last_pid != pid:
            self.last_pids[name] = pid
            self.start_times[name] = time.time()
            self.failure_counts[name] = 0
            self.last_accept_ts.pop(name, None)

        retcode = transport.process.poll()
        if retcode is not None:
            return self._register_failure(name), None

        if self._in_grace(name):
            return "warming", None

        health_cfg = (transport.spec or {}).get("health", {})
        mode = health_cfg.get("mode")
        if mode == "ephemeral":
            status, details = self._check_ephemeral(name, transport, health_cfg)
            if status == "healthy":
                self.failure_counts[name] = 0
            return status, details

        self.failure_counts[name] = 0
        return "healthy", None

    def _register_failure(self, name: str) -> str:
        if self._in_grace(name):
            return "warming"
        failures = self.failure_counts.get(name, 0) + 1
        self.failure_counts[name] = failures
        if failures >= self.policy.failure_threshold:
            return "unhealthy"
        return "warming"

    def _in_grace(self, name: str) -> bool:
        start = self.start_times.get(name)
        if start is None:
            self.start_times[name] = time.time()
            return True
        return (time.time() - start) < self.policy.probe_grace_seconds

    def _check_ephemeral(
        self,
        name: str,
        transport: NetcatTransport,
        health_cfg: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        spec = transport.spec or {}
        protocol = spec.get("protocol")
        mode = spec.get("mode")
        window_sec = float(health_cfg.get("window_sec", 10))

        if protocol == "ssl" and mode == "listen":
            if self._probe_ssl(spec):
                self.last_accept_ts[name] = time.time()

        last_accept = self.last_accept_ts.get(name)
        now = time.time()
        age_ms = None
        if last_accept is not None:
            age_ms = int((now - last_accept) * 1000)

        details = {
            "mode": "ephemeral",
            "window_sec": window_sec,
        }
        if age_ms is not None:
            details["last_accept_age_ms"] = age_ms

        if last_accept is not None and (now - last_accept) <= window_sec:
            return "healthy", details
        return self._register_failure(name), details

    def _probe_ssl(self, spec: Dict[str, Any]) -> bool:
        host = spec.get("host", "127.0.0.1")
        port = spec.get("port")
        if not port:
            return False
        try:
            sock = socket.create_connection((host, int(port)), timeout=1)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            tls_sock = context.wrap_socket(sock, server_hostname=host)
            tls_sock.do_handshake()
            tls_sock.close()
            return True
        except Exception:
            return False

    def _check_port(self, runtime: Runtime, port: Any) -> str:
        probe = port.probe or {}
        probe_path = probe.get("path")
        if not probe_path:
            probe_path = port.path
        if not probe_path:
            if port.direction == "inout":
                probe_path = os.path.join(runtime.board.board_path, runtime.board.socket_dir, f"{port.name}.in.fifo")
            else:
                probe_path = os.path.join(runtime.board.board_path, runtime.board.socket_dir, f"{port.name}.fifo")
        if not os.path.isabs(probe_path):
            probe_path = os.path.join(runtime.board.board_path, probe_path)

        if not os.path.exists(probe_path):
            return "unhealthy"
        try:
            stat_info = os.stat(probe_path)
            import stat

            return "healthy" if stat.S_ISFIFO(stat_info.st_mode) else "unhealthy"
        except Exception:
            return "unknown"

    def heal(self, runtime: Runtime, emitter: Any) -> Runtime:
        """Heal unhealthy resources by recreating them.

        Args:
            runtime: Current runtime state
            emitter: Trace emitter

        Returns:
            Updated runtime with healed resources
        """
        from .trace import emit_heal_trace

        current_time = time.time()
        healed = []

        for name, status in runtime.health_state.items():
            if status != "unhealthy":
                continue

            last_heal = self.last_heal_time.get(name, 0)
            if current_time - last_heal < self.policy.restart_delay:
                continue

            if name in runtime.transports:
                transport = runtime.transports[name]
                if isinstance(transport, FIFOTransport):
                    runtime = self._heal_fifo(runtime, name, transport)
                    healed.append(name)
                    emit_heal_trace(emitter, name, "port_rematerialized")
                elif isinstance(transport, NetcatTransport):
                    runtime = self._heal_netcat(runtime, name, transport)
                    healed.append(name)
                    emit_heal_trace(emitter, name, "restart_transport")
            elif name in runtime.processes:
                runtime = self._heal_process(runtime, name)
                healed.append(name)
                emit_heal_trace(emitter, name, "restart_process")

            self.last_heal_time[name] = current_time

        if healed:
            print(f"[health] Healed resources: {', '.join(healed)}")
            for name in healed:
                if name in runtime.health_state:
                    runtime.health_state[name] = "unknown"

        return runtime

    def _heal_fifo(self, runtime: Runtime, name: str, fifo: FIFOTransport) -> Runtime:
        """Heal a FIFO by recreating it."""
        print(f"[health] Healing FIFO: {name}")

        if os.path.exists(fifo.path):
            try:
                os.unlink(fifo.path)
            except Exception as e:
                print(f"[health] Error removing old FIFO {name}: {e}", file=sys.stderr)

        try:
            os.mkfifo(fifo.path)
            fifo.created = True
            print(f"[health] FIFO recreated: {name}")
        except Exception as e:
            print(f"[health] Error recreating FIFO {name}: {e}", file=sys.stderr)

        return runtime

    def _heal_netcat(self, runtime: Runtime, name: str, transport: NetcatTransport) -> Runtime:
        """Heal a netcat transport by restarting the process."""
        print(f"[health] Healing netcat transport: {name}")
        if transport.process:
            try:
                transport.process.kill()
                transport.process.wait(timeout=5)
            except Exception as e:
                print(f"[health] Error killing netcat process: {e}", file=sys.stderr)

        try:
            proc = _start_netcat(transport)
            transport.process = proc
            print(f"[health] Netcat transport restarted: {name} (PID {proc.pid})")
        except Exception as e:
            print(f"[health] Error restarting netcat {name}: {e}", file=sys.stderr)
        return runtime

    def _heal_process(self, runtime: Runtime, name: str) -> Runtime:
        """Heal a process by restarting it."""
        print(f"[health] Healing process: {name}")

        if name in runtime.processes:
            proc = runtime.processes[name]
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception as e:
                print(f"[health] Error killing process {name}: {e}", file=sys.stderr)

        return runtime


def _start_netcat(transport: NetcatTransport) -> subprocess.Popen:
    fifo_in = transport.fifo_in_path
    fifo_out = transport.fifo_out_path
    if not fifo_in and not fifo_out:
        raise RuntimeError("missing FIFO paths")

    stdin_handle = None
    stdout_handle = None
    try:
        if fifo_in:
            fd_in = os.open(fifo_in, os.O_RDWR)
            stdin_handle = os.fdopen(fd_in, "r+b", buffering=0)
        if fifo_out:
            fd_out = os.open(fifo_out, os.O_RDWR)
            stdout_handle = os.fdopen(fd_out, "r+b", buffering=0)

        proc = subprocess.Popen(
            ["lattice-netcat"] + transport.args,
            stdin=stdin_handle,
            stdout=stdout_handle,
            stderr=subprocess.PIPE,
        )
    finally:
        if stdout_handle:
            stdout_handle.close()
        if stdin_handle:
            stdin_handle.close()

    return proc
