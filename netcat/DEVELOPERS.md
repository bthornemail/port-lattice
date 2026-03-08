# Developers Guide: lib-lattice-netcat

This guide covers development, testing, and integration of
`lattice-netcat` as a transport layer in POSIX lattice environments.

## Goals

- Stay POSIX-compatible.
- Prefer system tools when available (nc, socat, openssl).
- Provide deterministic behavior for lattice runtime usage.
- Avoid non-portable flags and GNU-only tooling.

## Layout

- `lattice-netcat`: main shell script implementation.
- `test-lattice-netcat.sh`: integration tests.
- `lattice-netcat.mdoc`: manpage source.
- `docs/`: lattice runtime contract and board schema.

## Coding Standards

- POSIX shell syntax only.
- Use `printf` over `echo` when formatting is needed.
- Avoid ANSI color output to keep logs parseable.
- Keep fallbacks ordered: nc -> socat -> portable.

## Adding Features

1. Update `lattice-netcat` with new flags or behavior.
2. Extend `show_help` usage text.
3. Add/extend tests in `test-lattice-netcat.sh`.
4. Update `lattice-netcat.mdoc` and `README.md`.

## Manpage

The manpage is in `lattice-netcat.mdoc`. To render on a system with
mandoc:

```sh
mandoc -Tman lattice-netcat.mdoc > lattice-netcat.1
man ./lattice-netcat.1
```

## Testing

```sh
./test-lattice-netcat.sh
```

Notes:
- UDP and Unix socket tests may require `nc` or `socat`.
- SSL tests are exercised in manual runs if openssl is installed.

## Lattice Integration

`lattice-netcat` is intended to be spawned by the lattice runtime as a
transport. For SSH tunnels, use the runtime board compiler to declare
ports and let the runtime manage pid files and health.

Runtime observability:

- `state/health.json` tracks probe results.
- `state/traces/trace.log` captures compile/reconcile/probe/heal events.
- `lattice trace-resolve` validates trace logs and exports ULP bindings.

## Release Checklist

- `./test-lattice-netcat.sh` passes.
- `lattice-netcat --help` is accurate.
- `lattice-netcat.mdoc` reflects the current flags.
- README is current.
