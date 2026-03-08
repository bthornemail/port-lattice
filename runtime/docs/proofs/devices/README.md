# Device Proof Packets

Each device capture provides a self-contained evidence packet for the
protocol-matrix projection. Collect all files under a stable device id.

## Directory Layout

```
docs/proofs/devices/<device-id>/
  env.txt
  uname.txt
  kernel.txt
  openssl.txt
  lattice-runtime.txt
  lattice-netcat.txt
  protocol-matrix/
    tcp.out
    udp.out
    ssl.out
    trace.log
    health.json
    run.log
    hashes.txt
```

## Collection Script (example)

```bash
DEVICE_ID=$(hostname)
BASE=docs/proofs/devices/$DEVICE_ID
mkdir -p "$BASE/protocol-matrix"

date -u > "$BASE/env.txt"
uname -a > "$BASE/uname.txt"
python3 --version > "$BASE/kernel.txt" 2>&1 || python --version > "$BASE/kernel.txt" 2>&1
openssl version > "$BASE/openssl.txt" 2>/dev/null || true
./lattice --help 2>/dev/null | head -n 2 > "$BASE/lattice-runtime.txt" || true
lattice-netcat --help 2>/dev/null | head -n 2 > "$BASE/lattice-netcat.txt" || true

rm -rf examples/protocol-matrix/state
lsof -ti :9101 -ti :9102 -ti :9103 2>/dev/null | xargs -r kill -9
PATH=/home/main/github/lattice-netcat:$PATH ./lattice run examples/protocol-matrix > "$BASE/protocol-matrix/run.log" 2>&1 &
MATRIX_PID=$!
sleep 2
printf "tcp-ok\n" | timeout 5 nc -w 1 127.0.0.1 9101
printf "udp-ok\n" | timeout 5 nc -u -w 1 127.0.0.1 9102
printf "ssl-ok\n" | timeout 5 socat - OPENSSL:127.0.0.1:9103,verify=0 >/dev/null 2>&1
sleep 2
kill $MATRIX_PID 2>/dev/null || true
wait $MATRIX_PID 2>/dev/null || true

cp examples/protocol-matrix/state/received/tcp.out "$BASE/protocol-matrix/tcp.out"
cp examples/protocol-matrix/state/received/udp.out "$BASE/protocol-matrix/udp.out"
cp examples/protocol-matrix/state/received/ssl.out "$BASE/protocol-matrix/ssl.out"
cp examples/protocol-matrix/state/traces/trace.log "$BASE/protocol-matrix/trace.log"
cp examples/protocol-matrix/state/health.json "$BASE/protocol-matrix/health.json"
cp docs/proofs/protocol-matrix-hashes.txt "$BASE/protocol-matrix/hashes.txt"
```

Adjust paths if your proof artifacts are stored elsewhere.
