# Trace Schema

Trace logs are JSON Lines written to `state/traces/trace.log`.

## Event Fields

- `version`: schema version (`lattice-trace-1`)
- `id`: deterministic event id (sha256 of board_hash + seq + payload)
- `seq`: monotonically increasing sequence per run
- `ts`: unix timestamp
- `type`: event type (`compile`, `reconcile`, `probe`, `heal`, `kernel`, `validate_error`, `warnings`)
- `payload`: event payload (event-specific)
- `board_hash`: hash of the board snapshot that produced the event
- `gen`: board generation counter
- `ulp`: ULP binding representation derived from the event

## Reconcile Actions

`reconcile` payload actions are structural:
- `port_materialized`
- `transport_attached`
- `transport_detached`
- `process_started`

## Heal Actions

`heal` payload actions:
- `port_rematerialized`
- `restart_transport`
- `restart_process`

## Kernel Actions

`kernel` payload actions:
- `blast_analyzed`
- `blast_refused`
- `blast_accepted`

## Probe Status Values

- `healthy`
- `unhealthy`
- `unknown`
- `warming`

Probe payloads may include additional fields:
- `last_accept_age_ms`: milliseconds since last successful accept (ephemeral mode).

## ULP Binding Fields

- `version`: `ulp-calculus-1.0`
- `procedure`: `runtime_tick`
- `interrupt`: `event::<type>`
- `result`: polynomial string (e.g. `+1*runtime +1*event_probe`)
- `atoms`: list of atoms in the polynomial
- `hash`: binding hash (sha256 truncated to 16)

## Resolver

`lattice trace-resolve` validates trace logs against a board snapshot and can
export ULP bindings as JSON Lines:

```sh
lattice trace-resolve state/traces/trace.log --board ./board \
  --export-ulp state/traces/ulp.jsonl
```
