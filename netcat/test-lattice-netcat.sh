#!/bin/sh
set -eu

echo "=== Testing lattice-netcat ==="

TIMEOUT=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT="timeout 3"
fi

kill_tree() {
  # Best-effort kill of a process and its direct children (portable enough for CI).
  # lattice-netcat may spawn external helpers (nc/socat/openssl) that won't die if the wrapper dies.
  _pid="$1"
  if [ -z "${_pid}" ]; then
    return 0
  fi
  if command -v pkill >/dev/null 2>&1; then
    pkill -TERM -P "${_pid}" 2>/dev/null || true
  fi
  kill "${_pid}" 2>/dev/null || true
}

# Test 1: TCP echo server and client
printf "Test 1: TCP echo\n"
./lattice-netcat -l -p 9999 -e "/bin/cat" &
SERVER_PID=$!
sleep 1
printf "Hello TCP\n" | $TIMEOUT ./lattice-netcat -t 2 localhost 9999 || true
kill_tree $SERVER_PID
wait $SERVER_PID 2>/dev/null || true

# Test 2: UDP
printf "\nTest 2: UDP\n"
./lattice-netcat -u -l -p 9998 &
UDP_PID=$!
sleep 1
printf "Hello UDP\n" | $TIMEOUT ./lattice-netcat -t 2 -u localhost 9998 || true
kill_tree $UDP_PID
wait $UDP_PID 2>/dev/null || true

# Test 3: Unix sockets
printf "\nTest 3: Unix socket\n"
SOCKET="/tmp/test-$$.sock"
./lattice-netcat -U -l -L "$SOCKET" >/dev/null 2>&1 &
UNIX_PID=$!
sleep 1
ERR="/tmp/lattice-netcat-unix-$$.err"
rm -f "$ERR"
printf "Hello Unix\n" | $TIMEOUT ./lattice-netcat -t 2 -U -L "$SOCKET" >/dev/null 2>"$ERR" || true
if grep -q "Cannot connect to Unix socket" "$ERR" 2>/dev/null; then
  cat "$ERR" >&2 || true
  exit 1
fi
rm -f "$ERR"
kill_tree $UNIX_PID
wait $UNIX_PID 2>/dev/null || true
rm -f "$SOCKET"

# Test 4: FIFO mode
printf "\nTest 4: FIFO mode\n"
FIFO="/tmp/test-$$.fifo"
./lattice-netcat --fifo="$FIFO" &
FIFO_PID=$!
sleep 1
printf "Hello FIFO\n" > "$FIFO" &
cat "$FIFO" >/dev/null &
sleep 1
kill_tree $FIFO_PID
wait $FIFO_PID 2>/dev/null || true
rm -f "$FIFO"

# Test 5: Port scan
printf "\nTest 5: Port scan (localhost)\n"
./lattice-netcat -z -w 1 localhost 20-25 || true

# Test 6: Seam envelope transport (manifest+pull)
printf "\nTest 6: Seam envelope transport (manifest+pull)\n"
./tests/seam_transport.sh

printf "\n=== All tests completed ===\n"
