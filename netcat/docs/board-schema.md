# Board Schema

A board is a directory with JSON files. It is the authoritative lattice definition.

## Layout

```
BOARD/
  board.json
  peers.d/*.json
  ports.d/*.json
  procs.d/*.json
  health.d/health.json
  env.d/*.sh   (generated)
  state/       (runtime)
```

## Drop-in Merge Semantics

- Base `board.json` is loaded first.
- Drop-ins are applied in sorted filename order.
- Duplicate names are allowed; last write wins.
- Runtime emits warnings for overrides in trace logs.

## board.json

```
{
  "node_id": "local",
  "socket_dir": "state/sockets",
  "peers": [],
  "ports": [],
  "procs": [],
  "health": {
    "tick_seconds": 2,
    "restart_delay": 1
  }
}
```

## peers

```
{
  "name": "edge",
  "host": "example.com",
  "ssh_user": "lattice",
  "ssh_port": 22,
  "ssh_key": "/path/to/key",
  "options": ["StrictHostKeyChecking=no"]
}
```

## ports

```
{
  "name": "input",
  "type": "fifo",
  "path": "state/input.fifo"
}
```

### Optional Probe Overrides

Ports can override probe behavior via a `probe` object:

```
{
  "name": "api",
  "type": "tcp",
  "host": "0.0.0.0",
  "port": 9000,
  "probe": {
    "type": "tcp",
    "host": "127.0.0.1",
    "port": 9000
  }
}
```

```
{
  "name": "peer-tunnel",
  "type": "ssh_forward",
  "peer": "edge",
  "local_port": 9100,
  "remote_host": "localhost",
  "remote_port": 9100
}
```

## procs

```
{
  "name": "worker",
  "command": "./bin/worker --in $LATTICE_PORT_INPUT",
  "waits": ["input"],
  "fires": ["output"],
  "env": {
    "WORKER_MODE": "fast"
  }
}
```

## health

```
{
  "tick_seconds": 2,
  "restart_delay": 1
}
```
