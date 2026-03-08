# Protocol Matrix Example

This board exercises TCP, UDP, and SSL netcat projections in one lattice.
SSL health is configured as ephemeral and is considered healthy when at least
one handshake occurs inside the health window.

## Run

```bash
./lattice run examples/protocol-matrix
```

## Send Test Payloads

```bash
echo "tcp-ok" | lattice-netcat 127.0.0.1 9101
echo "udp-ok" | lattice-netcat -u 127.0.0.1 9102
echo "ssl-ok" | lattice-netcat -S 127.0.0.1 9103
```

## Inspect Results

```bash
cat examples/protocol-matrix/state/received/tcp.out
cat examples/protocol-matrix/state/received/udp.out
cat examples/protocol-matrix/state/received/ssl.out
```

## Kernel Gate

Kernel gating is disabled by default. To enable it, replace the board file with
`board.kernel.json` and ensure `lattice-kernel` is on PATH:

```bash
cp examples/protocol-matrix/board.kernel.json examples/protocol-matrix/board.json
./lattice run examples/protocol-matrix
```
