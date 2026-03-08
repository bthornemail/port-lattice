#!/usr/bin/env python3
"""Resolve lattice trace logs against a board snapshot."""

import argparse
import json
import os
from hashlib import sha256
from typing import List

from board import board_to_dict, read_board
from trace_schema import event_to_binding


def load_events(trace_path: str) -> List[dict]:
    events = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def resolve(trace_path: str, board_dir: str | None, export_ulp: str | None) -> int:
    events = load_events(trace_path)
    compile_events = [e for e in events if e.get("type") == "compile"]
    bindings = []

    if board_dir:
        board = read_board(os.path.abspath(board_dir))
        board_hash = sha256(
            json.dumps(board_to_dict(board), sort_keys=True).encode()
        ).hexdigest()
        mismatches = [e for e in events if e.get("board_hash") and e.get("board_hash") != board_hash]
        if mismatches:
            print(f"Board hash mismatch in {len(mismatches)} events")
            return 1

    for event in events:
        binding = event.get("ulp") or event_to_binding(event.get("type", ""), event.get("payload", {}))
        bindings.append(binding)

    if export_ulp:
        with open(export_ulp, "w", encoding="utf-8") as f:
            for binding in bindings:
                f.write(json.dumps(binding) + "\n")

    print(f"Events: {len(events)}")
    print(f"Compile events: {len(compile_events)}")
    if board_dir:
        print("Board hash matched compile events")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve lattice traces")
    parser.add_argument("trace", help="Path to trace.log")
    parser.add_argument("--board", help="Board directory to verify")
    parser.add_argument("--export-ulp", help="Write ULP bindings as JSONL")
    args = parser.parse_args()

    raise SystemExit(resolve(args.trace, args.board, args.export_ulp))


if __name__ == "__main__":
    main()
