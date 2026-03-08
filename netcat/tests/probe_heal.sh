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
  "node_id": "test",
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
  },
  {
    "name": "unix",
    "type": "unix",
    "path": "$TMP/state/test.sock",
    "probe": {
      "type": "unix",
      "path": "$TMP/state/test.sock"
    }
  }
]
EOF

# Start a temporary unix socket server for probing
python3 - <<PY &
import socket
s = socket.socket(socket.AF_UNIX)
s.bind("$TMP/state/test.sock")
s.listen(1)
s.settimeout(3)
try:
    s.accept()
except Exception:
    pass
finally:
    s.close()
PY
UNIX_PID=$!

# First run creates FIFO and probes unix socket
"$ROOT/lattice" run "$TMP" --once
kill $UNIX_PID 2>/dev/null || true

python3 - <<PY
import json, sys
with open("$TMP/state/health.json", "r", encoding="utf-8") as f:
    health = json.load(f)
status = health["resources"]["port:input"]["status"]
if status != "healthy":
    print("unexpected status", status)
    sys.exit(1)
unix_status = health["resources"]["port:unix"]["status"]
if unix_status != "healthy":
    print("unexpected unix status", unix_status)
    sys.exit(1)
PY

# Remove FIFO, run again to heal
rm -f "$TMP/state/input.fifo"
"$ROOT/lattice" run "$TMP" --once

if [ ! -p "$TMP/state/input.fifo" ]; then
  echo "fifo not healed"
  exit 1
fi

printf "probe_heal ok\n"
