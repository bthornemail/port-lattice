#!/bin/sh
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)

cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT

mkdir -p "$TMP/ports.d" "$TMP/state"
cat > "$TMP/board.json" <<'EOF'
{
  "node_id": "trace",
  "socket_dir": "state/sockets",
  "ports": [],
  "procs": []
}
EOF

cat > "$TMP/ports.d/ports.json" <<EOF
[
  {
    "name": "input",
    "type": "fifo",
    "path": "$TMP/state/input.fifo"
  }
]
EOF

"$ROOT/lattice" run "$TMP" --once

TRACE_PATH="$TMP/state/traces/trace.log"
ULP_OUT="$TMP/state/traces/ulp.jsonl"

"$ROOT/lattice" trace-resolve "$TRACE_PATH" --board "$TMP" --export-ulp "$ULP_OUT"

python3 - <<PY
import os, sys
if not os.path.exists("$ULP_OUT"):
    print("missing ulp output")
    sys.exit(1)
with open("$ULP_OUT", "r", encoding="utf-8") as f:
    lines = [line for line in f if line.strip()]
if not lines:
    print("empty ulp output")
    sys.exit(1)
PY

printf "trace_resolve ok\n"
