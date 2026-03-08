#!/bin/sh
set -eu

FIFO=${1:-/tmp/lattice-netcat.fifo}

./lattice-netcat --fifo="$FIFO" &
NETCAT_PID=$!

sleep 1
printf "hello fifo\n" > "$FIFO" &
cat "$FIFO" >/dev/null &

sleep 1
kill $NETCAT_PID 2>/dev/null || true
wait $NETCAT_PID 2>/dev/null || true
rm -f "$FIFO"
