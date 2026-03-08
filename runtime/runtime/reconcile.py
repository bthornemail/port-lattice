#!/usr/bin/env python3
"""Reconcile: converge POSIX resources to match ConnectionLattice."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from .types import (
    ConnectionLattice,
    FIFOTransport,
    NetcatTransport,
    Process,
    Runtime,
)


def reconcile(
    runtime: Runtime,
    old_lattice: Optional[ConnectionLattice],
    new_lattice: ConnectionLattice,
    emitter: Any  # TraceEmitter
) -> Runtime:
    """Reconcile POSIX resources to match new lattice.

    This function is idempotent and safe to call repeatedly.

    Args:
        runtime: Current runtime state
        old_lattice: Previous lattice (None on first tick)
        new_lattice: Target lattice to converge to

    Returns:
        Updated runtime state
    """
    print("[reconcile] Converging to new lattice definition")

    socket_dir = os.path.join(runtime.board.board_path, new_lattice.socket_dir)
    Path(socket_dir).mkdir(parents=True, exist_ok=True)

    runtime = _reconcile_fifos(runtime, new_lattice, emitter)
    runtime = _reconcile_netcat(runtime, old_lattice, new_lattice, emitter)
    runtime = _reconcile_processes(runtime, old_lattice, new_lattice, emitter)

    return runtime


def _reconcile_fifos(runtime: Runtime, lattice: ConnectionLattice, emitter: Any) -> Runtime:
    """Create FIFOs if they don't exist (idempotent)."""
    from .trace import emit_reconcile_trace

    for fifo in lattice.fifos:
        if not os.path.exists(fifo.path):
            print(f"[reconcile] Creating FIFO: {fifo.name} at {fifo.path}")
            try:
                os.mkfifo(fifo.path)
                fifo.created = True
                runtime.transports[fifo.name] = fifo
                emit_reconcile_trace(emitter, fifo.name, "port_materialized")
            except FileExistsError:
                fifo.created = True
                runtime.transports[fifo.name] = fifo
            except Exception as e:
                print(f"[reconcile] Error creating FIFO {fifo.name}: {e}", file=sys.stderr)
        else:
            fifo.created = True
            runtime.transports[fifo.name] = fifo

    return runtime


def _reconcile_processes(
    runtime: Runtime,
    old_lattice: Optional[ConnectionLattice],
    new_lattice: ConnectionLattice,
    emitter: Any
) -> Runtime:
    """Reconcile processes (start missing, stop removed)."""
    old_procs = {p.name: p for p in (old_lattice.processes if old_lattice else [])}
    new_procs = {p.name: p for p in new_lattice.processes}

    for proc_name in set(old_procs.keys()) - set(new_procs.keys()):
        if proc_name in runtime.processes:
            print(f"[reconcile] Stopping process: {proc_name}")
            try:
                proc = runtime.processes[proc_name]
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                print(f"[reconcile] Error stopping {proc_name}: {e}")
            del runtime.processes[proc_name]

    for proc_name, proc in new_procs.items():
        if proc_name not in runtime.processes:
            dependencies_ready = True
            for wait_port in proc.waits:
                port_path = new_lattice.get_port_path(wait_port, role="wait")
                if not port_path or not os.path.exists(port_path):
                    dependencies_ready = False
                    break
            for fire_port in proc.fires:
                port_path = new_lattice.get_port_path(fire_port, role="fire")
                if not port_path or not os.path.exists(port_path):
                    dependencies_ready = False
                    break

            if dependencies_ready:
                runtime = _start_process(runtime, proc, new_lattice, emitter)
            else:
                print(f"[reconcile] Waiting for dependencies: {proc_name}")

    return runtime


def _reconcile_netcat(
    runtime: Runtime,
    old_lattice: Optional[ConnectionLattice],
    new_lattice: ConnectionLattice,
    emitter: Any
) -> Runtime:
    """Start/stop netcat transports based on compiled lattice."""
    from .trace import emit_reconcile_trace

    old_nc = {t.name: t for t in (old_lattice.netcat_transports if old_lattice else [])}
    new_nc = {t.name: t for t in new_lattice.netcat_transports}

    for name in set(old_nc.keys()) - set(new_nc.keys()):
        if name in runtime.transports:
            transport = runtime.transports[name]
            if hasattr(transport, "process") and transport.process:
                try:
                    transport.process.terminate()
                    transport.process.wait(timeout=5)
                except Exception:
                    pass
            del runtime.transports[name]
            emit_reconcile_trace(emitter, name, "transport_detached")

    for name, transport in new_nc.items():
        needs_start = False
        if name not in runtime.transports:
            needs_start = True
        else:
            old_transport = old_nc.get(name)
            if not old_transport or old_transport.args != transport.args:
                needs_start = True
                existing = runtime.transports.get(name)
                if existing and hasattr(existing, "process") and existing.process:
                    try:
                        existing.process.terminate()
                        existing.process.wait(timeout=5)
                    except Exception:
                        pass

        if needs_start:
            if not transport.fifo_in_path and not transport.fifo_out_path:
                print(f"[reconcile] Error: transport {name} missing FIFO paths", file=sys.stderr)
                continue
            try:
                proc = _start_netcat(transport)
                transport.process = proc
                runtime.transports[name] = transport
                emit_reconcile_trace(emitter, name, "transport_attached")
            except Exception as e:
                print(f"[reconcile] Error starting netcat {name}: {e}", file=sys.stderr)

    return runtime


def _start_process(runtime: Runtime, proc: Process, lattice: ConnectionLattice, emitter: Any) -> Runtime:
    """Start a process with proper environment."""
    from .trace import emit_reconcile_trace

    print(f"[reconcile] Starting process: {proc.name}")

    env = os.environ.copy()
    env["LATTICE_NODE_ID"] = lattice.node_id
    env["LATTICE_SOCKET_DIR"] = lattice.socket_dir

    for port_name in proc.waits + proc.fires:
        port_path = lattice.get_port_path(port_name, role="wait" if port_name in proc.waits else "fire")
        if port_path:
            env_var = f"LATTICE_PORT_{port_name.upper()}"
            env[env_var] = port_path

    env.update(proc.env)

    command = proc.command
    for key, value in env.items():
        command = command.replace(f"${key}", value)

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        runtime.processes[proc.name] = process
        print(f"[reconcile] Process started: {proc.name} (PID {process.pid})")
        emit_reconcile_trace(emitter, proc.name, "process_started")
    except Exception as e:
        print(f"[reconcile] Error starting process {proc.name}: {e}", file=sys.stderr)

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
