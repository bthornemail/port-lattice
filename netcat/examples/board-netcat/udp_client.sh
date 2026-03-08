#!/bin/sh
set -eu

OUT=/tmp/lattice-udp.out

while true; do
  printf "ping udp\n" | ./lattice-netcat -u --udp-wait 1 127.0.0.1 9994 > "$OUT" 2>/dev/null || true
  if [ ! -s "$OUT" ]; then
    printf "no response\n" > "$OUT"
  fi
  sleep 2
 done
