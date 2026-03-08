A board is a directory with JSON files. It is the authoritative lattice definition.

Directory layout:

```
board/
  board.json
  peers.d/*.json
  ports.d/*.json
  transports.d/*.json
  procs.d/*.json
  health.d/health.json
  state/
```

## board.json

Minimal example:

```json
{
  "node_id": "local",
  "socket_dir": "state/sockets",
  "ports": [],
  "transports": [],
  "procs": [],
  "health": {
    "tick_seconds": 2,
    "restart_delay": 1
  }
}
```

## ports

Ports are FIFO-first structural endpoints. Every port materializes as a FIFO.

```json
{
  "name": "input",
  "direction": "in",
  "path": "state/sockets/input.fifo",
  "probe": {
    "path": "state/sockets/input.fifo"
  }
}
```

Fields:
- `name` (required): Port name.
- `direction` (optional): `in`, `out`, or `inout`. Default `inout`.
- `path` (optional): FIFO path. Relative paths are resolved against the board.
- `probe` (optional): Override probe path. Probes are FIFO-only.

If `path` is omitted, the FIFO defaults to `${socket_dir}/${name}.fifo`.
If `direction` is `inout`, the runtime splits this into two FIFOs:

- `${name}.in.fifo` (external → lattice)
- `${name}.out.fifo` (lattice → external)

Environment exports include:
- `LATTICE_PORT_<NAME>_IN`
- `LATTICE_PORT_<NAME>_OUT`

## transports

Transports are projections that attach to FIFO ports. They never define ports.

```json
{
  "name": "tcp-listener",
  "kind": "netcat",
  "attach": "input",
  "spec": {
    "protocol": "tcp",
    "mode": "listen",
    "port": 9999,
    "keep_open": true,
    "exec": "/bin/cat"
  }
}
```

Fields:
- `name` (required): Transport name.
- `kind` (required): `netcat` (currently the only supported kind).
- `attach` (required): Port name to attach.
- `spec` (required): Netcat specification.

Netcat spec:
- `protocol`: `tcp`, `udp`, `ssl`, or `unix`.
- `mode`: `listen` or `connect`.
- `host`: required for `connect` (non-unix).
- `port`: required for `tcp`/`udp`/`ssl`.
- `socket_path`: required for `unix`.
- `keep_open`: keep the listener open (`-k`).
- `exec`: command to exec (`-e`).
- `udp_wait`: seconds to wait for a UDP reply (`--udp-wait`).
- `health` (optional): transport health override (ephemeral modes).

Example transport health (ephemeral SSL semantics):

```json
{
  "health": {
    "mode": "ephemeral",
    "success_condition": "at_least_one_accept",
    "window_sec": 10,
    "heal": "restart_on_demand"
  }
}
```

## procs

Processes are POSIX commands. Use port exports for FIFO I/O.

```json
{
  "name": "worker",
  "command": "cat $LATTICE_PORT_INPUT > $LATTICE_PORT_OUTPUT",
  "waits": ["input"],
  "fires": ["output"],
  "env": {}
}
```

Processes should read from `LATTICE_PORT_<NAME>_IN` and write to
`LATTICE_PORT_<NAME>_OUT` when using duplex (`inout`) ports.

## health

Health policy fields:

- `tick_seconds`: reconcile tick interval.
- `restart_delay`: minimum delay between heals.
- `probe_grace_seconds`: grace period after start/restart.
- `failure_threshold`: consecutive failures before heal.

## drop-ins

Drop-in files in `ports.d/`, `transports.d/`, and `procs.d/` can contain either
one object or a list of objects. When names collide, later files override earlier
ones and a warning is emitted to the trace log.

## kernel

Kernel gating is optional and executed before POSIX reconcile. When enabled,
the runtime sends a JSON payload to an external `lattice-kernel` command.

```json
{
  "kernel": {
    "enabled": true,
    "command": ["lattice-kernel", "analyze"],
    "policy": "kernel/policy.json",
    "fail_open": false,
    "timeout_seconds": 10
  }
}
```

The kernel command must read JSON from stdin and emit JSON on stdout:

```json
{ "decision": "accept" }
```
