#!/usr/bin/env python3
import json
import os
import socket
import sys
from hashlib import sha256

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, RUNTIME)

from board import board_to_dict, read_board  # noqa: E402
from trace_schema import build_event  # noqa: E402

BOARD_DIR = os.path.abspath(os.path.dirname(__file__))
STATE_DIR = os.path.join(BOARD_DIR, "state")
TRACE_PATH = os.path.join(STATE_DIR, "traces", "trace.log")

os.makedirs(os.path.dirname(TRACE_PATH), exist_ok=True)

board = read_board(BOARD_DIR)
board_hash = sha256(json.dumps(board_to_dict(board), sort_keys=True).encode()).hexdigest()

result = "no_response"
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    sock.sendto(b"ping udp\n", ("127.0.0.1", 9994))
    data, _ = sock.recvfrom(2048)
    if data:
        result = "ok"
    sock.close()
except Exception:
    result = "no_response"

payload = {"port": 9994, "result": result}

event = build_event("udp_validate", payload, board_hash=board_hash)
with open(TRACE_PATH, "a", encoding="utf-8") as f:
    f.write(json.dumps(event) + "\n")
