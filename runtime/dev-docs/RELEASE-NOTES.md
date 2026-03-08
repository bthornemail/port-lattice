# Release Notes

## Current

- **Breaking**: FIFO-first port model. Ports are structural FIFOs only.
- **Breaking**: New `transports` section for projections; port `type` removed.
- Netcat projections (`kind: netcat`) for TCP/UDP/SSL/Unix via `lattice-netcat`.
- Optional kernel gate via external `lattice-kernel` (blast-radius analysis).
- Env export generation in `env.d/` with port direction metadata.
- Trace logging with ULP bindings and Coxeter export.
- Drop-in merge warnings emitted to traces.
- Health checks write `state/health.json` on every tick.

## Notes

- `trace-resolve` validates board hashes using runtime hashing.
