#!/bin/bash
# Test suite for lattice runtime

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer the merged port-lattice netcat utilities.
export PATH="$SCRIPT_DIR/../netcat:$PATH"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Test 1: Board validation
info "Test 1: Validating example boards"
./lattice validate examples/simple-board || fail "Simple board validation failed"
pass "Simple board validated"

# Test 2: Single tick execution
info "Test 2: Running single tick"
./lattice run examples/simple-board --once || fail "Single tick failed"
pass "Single tick completed"

# Test 3: FIFO creation
info "Test 3: Checking FIFO creation"
if [ ! -p examples/simple-board/state/sockets/input.fifo ]; then
    fail "Input FIFO not created"
fi
if [ ! -p examples/simple-board/state/sockets/output.fifo ]; then
    fail "Output FIFO not created"
fi
pass "FIFOs created correctly"

# Test 3b: Protocol matrix (TCP/UDP/SSL) if lattice-netcat exists
if command -v lattice-netcat >/dev/null 2>&1; then
    info "Test 3b: Protocol matrix (tcp/udp/ssl)"
    ./lattice run examples/protocol-matrix >/tmp/lattice-protocol.log 2>&1 &
    MATRIX_PID=$!
    sleep 2

    echo "tcp-ok" | timeout 5 nc -w 1 127.0.0.1 9101 || fail "TCP send failed"
    echo "udp-ok" | timeout 5 nc -u -w 1 127.0.0.1 9102 || fail "UDP send failed"
    echo "ssl-ok" | timeout 5 socat - OPENSSL:127.0.0.1:9103,verify=0 >/dev/null 2>&1 || fail "SSL send failed"

    sleep 2
    kill $MATRIX_PID 2>/dev/null || true
    wait $MATRIX_PID 2>/dev/null || true

    if [ ! -f examples/protocol-matrix/state/received/tcp.out ]; then
        fail "TCP output not recorded"
    fi
    if [ ! -f examples/protocol-matrix/state/received/udp.out ]; then
        fail "UDP output not recorded"
    fi
    if [ ! -f examples/protocol-matrix/state/received/ssl.out ]; then
        fail "SSL output not recorded"
    fi
    rg -q "tcp-ok" examples/protocol-matrix/state/received/tcp.out || fail "TCP payload missing"
    rg -q "udp-ok" examples/protocol-matrix/state/received/udp.out || fail "UDP payload missing"
    rg -q "ssl-ok" examples/protocol-matrix/state/received/ssl.out || fail "SSL payload missing"
    pass "Protocol matrix outputs recorded"
else
    info "Test 3b: Protocol matrix skipped (lattice-netcat not found)"
fi

# Test 4: Invalid board detection
info "Test 4: Testing invalid board detection"
mkdir -p /tmp/test-invalid-board
cat > /tmp/test-invalid-board/board.json <<EOF
{
  "node_id": "test",
  "socket_dir": "state",
  "ports": [
    {
      "name": "dup",
      "direction": "in"
    },
    {
      "name": "dup",
      "direction": "out"
    }
  ],
  "transports": [],
  "procs": [],
  "health": {"tick_seconds": 2, "restart_delay": 1}
}
EOF

if ./lattice validate /tmp/test-invalid-board 2>/dev/null; then
    fail "Invalid board should have failed validation"
fi
pass "Invalid board correctly rejected"

# Test 5: Missing dependencies detection
info "Test 5: Testing missing dependencies detection"
mkdir -p /tmp/test-missing-deps
cat > /tmp/test-missing-deps/board.json <<EOF
{
  "node_id": "test",
  "socket_dir": "state",
  "ports": [],
  "transports": [],
  "procs": [
    {
      "name": "worker",
      "command": "cat",
      "waits": ["nonexistent"],
      "fires": []
    }
  ],
  "health": {"tick_seconds": 2, "restart_delay": 1}
}
EOF

if ./lattice validate /tmp/test-missing-deps 2>/dev/null; then
    fail "Missing dependency should have failed validation"
fi
pass "Missing dependency correctly detected"

# Test 6: Drop-in files
info "Test 6: Testing drop-in files"
mkdir -p /tmp/test-dropin/{peers.d,ports.d,transports.d,procs.d,state}
cat > /tmp/test-dropin/board.json <<EOF
{
  "node_id": "test",
  "socket_dir": "state",
  "transports": [],
  "health": {"tick_seconds": 2, "restart_delay": 1}
}
EOF

cat > /tmp/test-dropin/ports.d/test-port.json <<EOF
{
  "name": "test-input",
  "direction": "in"
}
EOF

cat > /tmp/test-dropin/transports.d/test-transport.json <<EOF
{
  "name": "test-netcat",
  "kind": "netcat",
  "attach": "test-input",
  "spec": {
    "protocol": "tcp",
    "mode": "connect",
    "host": "127.0.0.1",
    "port": 1234
  }
}
EOF

./lattice validate /tmp/test-dropin || fail "Drop-in board validation failed"
pass "Drop-in files loaded correctly"

# Cleanup
info "Cleaning up test artifacts"
rm -rf /tmp/test-invalid-board /tmp/test-missing-deps /tmp/test-dropin
rm -rf examples/simple-board/state
rm -rf examples/protocol-matrix/state
lsof -ti :9101 -ti :9102 -ti :9103 2>/dev/null | xargs -r kill -9

echo ""
echo -e "${GREEN}All tests passed!${NC}"
