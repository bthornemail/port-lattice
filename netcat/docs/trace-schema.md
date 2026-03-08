# Trace Schema

Trace logs are JSON Lines written to `state/traces/trace.log`.

## Event Fields

- `version`: schema version (`lattice-trace-1`)
- `id`: deterministic event id (sha256 of event payload)
- `ts`: unix timestamp
- `type`: event type (`compile`, `reconcile`, `probe`, `heal`, `validate_error`, `warnings`)
- `payload`: event payload (event-specific)
- `board_hash`: hash of the board snapshot that produced the event
- `ulp`: ULP binding representation derived from the event

## ULP Binding Fields

- `version`: `ulp-calculus-1.0`
- `procedure`: `runtime_tick`
- `interrupt`: `event::<type>`
- `result`: polynomial string (e.g. `+1*runtime +1*event_probe`)
- `atoms`: list of atoms in the polynomial
- `hash`: binding hash (sha256 truncated to 16)
- `payload`: original event payload

## Resolver

`lattice trace-resolve` validates trace logs against a board snapshot and can
export ULP bindings as JSON Lines:

```sh
lattice trace-resolve state/traces/trace.log --board ./board \
  --export-ulp state/traces/ulp.jsonl
```
