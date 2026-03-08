# port-lattice

Unified transport layer for the closure spine.

This repository folder merges:
- `kernel/` (from `lattice-kernel`)
- `netcat/` (from `lattice-netcat`)
- `runtime/` (from `lattice-runtime`)

Design constraints:
- Transport only; no authority logic.
- Moves ULP seam envelope streams as NDJSON bytes.
- Anti-entropy hooks are allowed (digest-based pull), but merging and replay belong to `port-matroid`.

## Quick tests

```sh
./netcat/test-lattice-netcat.sh
./runtime/test-lattice.sh
```

## Contributor docs

- `docs/actual-functionality.md` explains implemented behavior across `runtime/`, `netcat/`, and trace/health flows.
- `docs/logic-ladder-and-invariants.md` maps the logic ladder and seven-invariant metastructure to current code.

## Seam envelope transport

```sh
# Serve an NDJSON file with a MANIFEST header and GET support
./netcat/seam-transport serve --port 39123 --file ./events.ndjson

# Pull if digest differs (writes to --out and verifies digest)
./netcat/seam-transport pull --port 39123 --out ./events.pulled.ndjson --local ./events.ndjson
```

# port-lattice
