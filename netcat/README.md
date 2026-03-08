# lib-lattice-netcat

POSIX-oriented netcat implementation for lattice runtime environments.

## Overview

`lattice-netcat` is a self-contained shell implementation that prefers
system tools (nc, socat, openssl) when present and falls back to portable
methods. It is designed for deterministic, observable network transports
in POSIX environments.

## Features

- TCP client/server
- UDP client/server
- Unix domain sockets
- SSL/TLS (via openssl or socat)
- FIFO mode for lattice pipelines
- Zero-I/O port scanning
- Exec mode (with socat)
- PID file and log file integration

## Install

```sh
chmod +x lattice-netcat
sudo install -m 755 lattice-netcat /usr/local/bin/
```

## Quick Usage

```sh
# TCP client
lattice-netcat example.com 80

# TCP server
lattice-netcat -l -p 8080

# UDP client
lattice-netcat -u example.com 53

# Unix socket server
lattice-netcat -U -l -L /tmp/test.sock

# SSL client
lattice-netcat -S example.com 443

# FIFO mode
lattice-netcat --fifo=/tmp/pipe.fifo
```

## Environment

- `LATTICE_NETCAT_DEBUG=1` enables shell tracing.
- `LATTICE_SSL_CERT`, `LATTICE_SSL_KEY`, `LATTICE_SSL_CA` configure SSL.
- `--udp-wait=SECONDS` waits for a UDP reply in client mode.

## Tests

```sh
./test-lattice-netcat.sh
```

## Documentation

- Man page source: `lattice-netcat.mdoc`
- Runtime contract: `docs/posix-lattice-contract.md`
- Board schema: `docs/board-schema.md`
- Trace schema: `docs/trace-schema.md`
- Trace resolver: `lattice trace-resolve <trace.log> --board <board-dir> --export-ulp <out.jsonl>`

## Seam Envelope Transport (ULP)

For ULP "seam envelope" NDJSON streams, lattice-netcat provides a transport-only mover with a minimal
anti-entropy hook (pull-by-digest). This does not interpret or merge events; it only moves bytes.

```sh
# Serve an NDJSON file with a MANIFEST header and GET support
./seam-transport serve --port 39123 --file ./events.ndjson

# Pull if digest differs (writes to --out and verifies digest)
./seam-transport pull --port 39123 --out ./events.pulled.ndjson --local ./events.ndjson
```

## Sample Boards

- `examples/board-netcat` runs TCP/UDP lattice-netcat servers and probes them.

## License

BSD 3-Clause License.
