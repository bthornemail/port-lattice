#!/usr/bin/env python3
"""Kernel adapter for blast-radius gating (external lattice-kernel)."""

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .types import Board, KernelConfig


class KernelGateError(RuntimeError):
    """Raised when kernel gate fails and fail_open is false."""


@dataclass
class KernelDecision:
    decision: str
    reason: str
    report: Dict[str, Any]
    report_hash: str
    policy_hash: Optional[str]

    def to_payload(self) -> Dict[str, Any]:
        payload = {
            "decision": self.decision,
            "reason": self.reason,
            "report_hash": self.report_hash,
        }
        if self.policy_hash:
            payload["policy_hash"] = self.policy_hash
        if "summary" in self.report:
            payload["summary"] = self.report["summary"]
        return payload


def run_kernel_gate(board: Board, previous_board: Optional[Board], config: KernelConfig) -> KernelDecision:
    if not config.command:
        raise KernelGateError("kernel.command is required")

    payload, policy_hash = _build_payload(board, previous_board, config)
    raw_payload = json.dumps(payload, sort_keys=True).encode()

    try:
        result = subprocess.run(
            config.command,
            input=raw_payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=config.timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if config.fail_open:
            return KernelDecision(
                decision="accept",
                reason=f"kernel_fail_open: {exc}",
                report={},
                report_hash=_hash_bytes(raw_payload),
                policy_hash=policy_hash,
            )
        raise KernelGateError(str(exc)) from exc

    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip() or "kernel failed"
        if config.fail_open:
            return KernelDecision(
                decision="accept",
                reason=f"kernel_fail_open: {message}",
                report={},
                report_hash=_hash_bytes(raw_payload),
                policy_hash=policy_hash,
            )
        raise KernelGateError(message)

    try:
        report = json.loads(result.stdout.decode())
    except json.JSONDecodeError as exc:
        if config.fail_open:
            return KernelDecision(
                decision="accept",
                reason=f"kernel_fail_open: invalid json: {exc}",
                report={},
                report_hash=_hash_bytes(raw_payload),
                policy_hash=policy_hash,
            )
        raise KernelGateError(f"invalid kernel JSON: {exc}") from exc

    decision = report.get("decision", "").lower()
    if decision not in {"accept", "refuse"}:
        if config.fail_open:
            return KernelDecision(
                decision="accept",
                reason="kernel_fail_open: invalid decision",
                report=report,
                report_hash=_hash_bytes(json.dumps(report, sort_keys=True).encode()),
                policy_hash=policy_hash,
            )
        raise KernelGateError("kernel decision must be accept|refuse")

    reason = report.get("reason", "kernel_decision")
    return KernelDecision(
        decision=decision,
        reason=reason,
        report=report,
        report_hash=_hash_bytes(json.dumps(report, sort_keys=True).encode()),
        policy_hash=policy_hash,
    )


def _build_payload(
    board: Board,
    previous_board: Optional[Board],
    config: KernelConfig,
) -> Tuple[Dict[str, Any], Optional[str]]:
    policy_hash = None
    policy = None
    if config.policy_path:
        policy_path = config.policy_path
        if not os.path.isabs(policy_path):
            policy_path = os.path.join(board.board_path, policy_path)
        with open(policy_path) as f:
            policy = json.load(f)
        policy_hash = _hash_bytes(json.dumps(policy, sort_keys=True).encode())

    payload: Dict[str, Any] = {
        "version": "lattice-kernel-gate-1",
        "board": _serialize_board(board),
    }
    if previous_board:
        payload["previous_board"] = _serialize_board(previous_board)
    if policy is not None:
        payload["policy"] = policy

    return payload, policy_hash


def _serialize_board(board: Board) -> Dict[str, Any]:
    return {
        "node_id": board.node_id,
        "socket_dir": board.socket_dir,
        "ports": [
            {"name": p.name, "direction": p.direction, "path": p.path}
            for p in board.ports
        ],
        "processes": [
            {
                "name": p.name,
                "command": p.command,
                "waits": p.waits,
                "fires": p.fires,
            }
            for p in board.procs
        ],
        "transports": [
            {"name": t.name, "kind": t.kind, "attach": t.attach, "spec": t.spec}
            for t in board.transports
        ],
    }


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
