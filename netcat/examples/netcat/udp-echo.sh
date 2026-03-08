#!/bin/sh
set -eu

PORT=${1:-9998}

./lattice-netcat -u -l -p "$PORT" &
SERVER_PID=$!

sleep 1
printf "hello udp\n" | ./lattice-netcat -u localhost "$PORT"

kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
