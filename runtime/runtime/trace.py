#!/usr/bin/env python3
"""Trace emission and ULP binding generation for lattice runtime."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class TraceEmitter:
    """Immutable trace log emitter (blackboard pattern)."""
    
    def __init__(self, board_path: str):
        self.board_path = Path(board_path)
        self.trace_dir = self.board_path / "state" / "traces"
        self.trace_log = self.trace_dir / "trace.log"
        self.board_hash: Optional[str] = None
        self.generation: Optional[int] = None
        self.sequence = 0
        
        # Ensure trace directory exists
        self.trace_dir.mkdir(parents=True, exist_ok=True)
    
    def set_board_hash(self, board_hash: str):
        """Set current board hash for event attribution."""
        self.board_hash = board_hash

    def set_generation(self, generation: int):
        """Set current generation for event attribution."""
        self.generation = generation
    
    def emit(self, event_type: str, payload: Dict[str, Any]):
        """Emit immutable trace event to blackboard.
        
        Args:
            event_type: Event type (compile, reconcile, probe, heal, etc)
            payload: Event-specific data
        """
        if not self.board_hash:
            # Compute ephemeral hash if not set
            self.board_hash = "unknown"
        
        self.sequence += 1
        event_id = self._compute_event_id(event_type, payload, self.sequence)

        # Create trace event
        event = {
            "version": "lattice-trace-1",
            "id": event_id,
            "seq": self.sequence,
            "ts": time.time(),
            "type": event_type,
            "payload": payload,
            "board_hash": self.board_hash,
            "ulp": self._compute_ulp_binding(event_type, payload)
        }
        if self.generation is not None:
            event["gen"] = self.generation
        
        # Append to immutable log
        with open(self.trace_log, 'a') as f:
            f.write(json.dumps(event) + "\n")
    
    def _compute_event_id(self, event_type: str, payload: Dict[str, Any], seq: int) -> str:
        """Content-addressable event ID."""
        canonical = json.dumps({
            "board_hash": self.board_hash,
            "seq": seq,
            "type": event_type,
            "payload": payload
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def _compute_ulp_binding(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert event to ULP polynomial representation.
        
        The ULP binding represents the event as a polynomial over atoms.
        This allows algebraic composition and analysis of traces.
        """
        atoms = self._extract_atoms(event_type, payload)
        result = " ".join(f"+1*{atom}" for atom in atoms)
        
        return {
            "version": "ulp-calculus-1.0",
            "procedure": "runtime_tick",
            "interrupt": f"event::{event_type}",
            "result": result,
            "atoms": atoms,
            "hash": self._truncate_hash(result)
        }
    
    def _extract_atoms(self, event_type: str, payload: Dict[str, Any]) -> List[str]:
        """Extract basis atoms from event payload.
        
        Atoms are the irreducible elements of the polynomial algebra.
        Each event contributes multiple atoms based on its structure.
        """
        atoms = ["runtime"]  # Base atom - all events involve runtime
        
        # Add event type atom
        atoms.append(f"event_{event_type}")
        
        # Extract context-specific atoms
        if "resource" in payload:
            atoms.append(f"resource_{payload['resource']}")
        
        if "action" in payload:
            atoms.append(f"action_{payload['action']}")
        
        if "status" in payload:
            atoms.append(f"status_{payload['status']}")
        
        if "coxeter" in payload:
            atoms.append(f"coxeter_{payload['coxeter']}")
        
        if "peer" in payload:
            atoms.append(f"peer_{payload['peer']}")
        
        if "port" in payload:
            atoms.append(f"port_{payload['port']}")
        
        if "process" in payload:
            atoms.append(f"process_{payload['process']}")
        
        return atoms
    
    def _truncate_hash(self, data: str) -> str:
        """Truncated hash for ULP binding identification."""
        full_hash = hashlib.sha256(data.encode()).hexdigest()
        return full_hash[:16]


def compute_board_hash(board: Any) -> str:
    """Compute content-addressable hash of board.
    
    This creates a deterministic fingerprint of the board state.
    All events emitted while this board is active are tagged with this hash.
    """
    # Convert board to dict for hashing
    board_dict = {
        "node_id": board.node_id,
        "socket_dir": board.socket_dir,
        "peers": [
            {
                "name": p.name,
                "host": p.host,
                "ssh_user": p.ssh_user,
                "ssh_port": p.ssh_port
            }
            for p in board.peers
        ],
        "ports": [
            {
                "name": p.name,
                "direction": p.direction,
                "path": p.path,
                "probe": p.probe
            }
            for p in board.ports
        ],
        "transports": [
            {
                "name": t.name,
                "kind": t.kind,
                "attach": t.attach,
                "spec": t.spec
            }
            for t in board.transports
        ],
        "procs": [
            {
                "name": p.name,
                "command": p.command,
                "waits": p.waits,
                "fires": p.fires,
                "env": p.env
            }
            for p in board.procs
        ],
        "kernel": {
            "enabled": board.kernel.enabled,
            "command": board.kernel.command,
            "policy_path": board.kernel.policy_path,
            "fail_open": board.kernel.fail_open,
            "timeout_seconds": board.kernel.timeout_seconds,
        }
    }
    
    canonical = json.dumps(board_dict, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def emit_compile_trace(emitter: TraceEmitter, lattice: Any):
    """Emit compile event trace."""
    payload = {
        "action": "compile",
        "num_fifos": len(lattice.fifos),
        "num_transports": len(lattice.netcat_transports),
        "num_processes": len(lattice.processes)
    }
    emitter.emit("compile", payload)


def emit_reconcile_trace(emitter: TraceEmitter, resource: str, action: str):
    """Emit reconcile event trace."""
    payload = {
        "resource": resource,
        "action": action
    }
    emitter.emit("reconcile", payload)


def emit_probe_trace(
    emitter: TraceEmitter,
    resource: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
):
    """Emit health probe trace."""
    payload = {
        "resource": resource,
        "status": status
    }
    if details:
        payload.update(details)
    emitter.emit("probe", payload)


def emit_heal_trace(emitter: TraceEmitter, resource: str, action: str):
    """Emit healing trace."""
    payload = {
        "resource": resource,
        "action": action
    }
    emitter.emit("heal", payload)


def emit_validation_error_trace(emitter: TraceEmitter, errors: List[str]):
    """Emit validation error trace."""
    payload = {
        "errors": errors
    }
    emitter.emit("validate_error", payload)


def emit_warning_trace(emitter: TraceEmitter, warnings: List[str]):
    """Emit warning trace."""
    payload = {
        "warnings": warnings
    }
    emitter.emit("warnings", payload)


def emit_kernel_trace(emitter: TraceEmitter, action: str, payload: Dict[str, Any]):
    """Emit kernel gate trace."""
    kernel_payload = {"action": action}
    kernel_payload.update(payload)
    emitter.emit("kernel", kernel_payload)
