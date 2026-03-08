#!/bin/sh
set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BOARD="$ROOT/examples/board-netcat"

ps -ef | rg 'lattice-netcat|udp_echo.py|udp_client.sh|udp_validate.py|socat|nc -u -l -p 9996' | rg -v 'rg lattice-netcat|ps -ef' | awk '{print $2}' | xargs -r kill -9 || true

rm -f /tmp/lattice-tcp.out /tmp/lattice-udp.out /tmp/lattice-netcat-demo.sock

for f in "$BOARD"/state/proc_*.pid; do
  [ -f "$f" ] || continue
  rm -f "$f"
done

if command -v ss >/dev/null 2>&1; then
  ss -lnp 2>/dev/null | rg '9997|9996|9995|9994' || true
fi

printf "cleanup ok\n"
