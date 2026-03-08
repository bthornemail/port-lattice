#!/bin/sh
set -eu

PORT=${1:-9999}

./lattice-netcat -l -p "$PORT" -k -e "/bin/cat" &
SERVER_PID=$!

sleep 1
printf "hello tcp\n" | ./lattice-netcat localhost "$PORT"

kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
