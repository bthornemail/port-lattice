#!/usr/bin/env python3
"""Trace schema and ULP binding mapping for lattice runtime events."""

import json
import re
import time
from hashlib import sha256
from typing import Any, Dict, Optional

SCHEMA_VERSION = "lattice-trace-1"
ULP_VERSION = "ulp-calculus-1.0"


def _now_ts() -> int:
    return int(time.time())


def _sanitize_atom(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def _binding_hash(procedure: str, interrupt: str, result: str) -> str:
    data = f"{procedure}:{interrupt}:{result}"
    return sha256(data.encode()).hexdigest()[:16]


def event_to_binding(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    event_atom = _sanitize_atom(f"event_{event_type}")
    atoms = ["runtime", event_atom]
    procedure = "runtime_tick"
    interrupt = f"event::{event_type}"
    result = "+1*runtime +1*" + event_atom
    return {
        "version": ULP_VERSION,
        "procedure": procedure,
        "interrupt": interrupt,
        "result": result,
        "atoms": atoms,
        "hash": _binding_hash(procedure, interrupt, result),
        "payload": payload,
    }


def build_event(
    event_type: str,
    payload: Dict[str, Any],
    board_hash: Optional[str] = None,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    event_ts = ts or _now_ts()
    event = {
        "version": SCHEMA_VERSION,
        "ts": event_ts,
        "type": event_type,
        "payload": payload,
        "board_hash": board_hash,
    }
    event["ulp"] = event_to_binding(event_type, payload)
    event_id = sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
    event["id"] = event_id
    return event
