#!/bin/sh
set -eu

PORT=${1:-8443}

./lattice-netcat -S -l -p "$PORT" -e "/bin/cat" &
SERVER_PID=$!

sleep 2
printf "hello ssl\n" | ./lattice-netcat -S localhost "$PORT"

kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
