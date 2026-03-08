#!/bin/sh
set -eu

SOCKET=${1:-/tmp/lattice-netcat.sock}

./lattice-netcat -U -l -L "$SOCKET" -e "/bin/cat" &
SERVER_PID=$!

sleep 1
printf "hello unix\n" | ./lattice-netcat -U -L "$SOCKET"

kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
rm -f "$SOCKET"
