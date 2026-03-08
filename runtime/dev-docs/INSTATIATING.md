# Instantiating a Lattice

This guide describes how to instantiate a lattice runtime from a board.

## 1. Create a Board

```
mkdir -p my-board/{ports.d,transports.d,procs.d,state/sockets}
```

Create `board.json`:

```json
{
  "node_id": "local",
  "socket_dir": "state/sockets",
  "ports": [],
  "transports": [],
  "procs": [],
  "health": {"tick_seconds": 2, "restart_delay": 1}
}
```

## 2. Add Ports

FIFO port:

```json
{
  "name": "input",
  "direction": "in",
  "path": "state/sockets/input.fifo"
}
```

## 3. Add Transports

Netcat TCP server attached to the FIFO:

```json
{
  "name": "tcp-echo",
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

## 4. Run

```bash
./lattice validate my-board
./lattice run my-board
```

## 5. Kernel Gate (Optional)

Add a `kernel` block to call an external `lattice-kernel` gate:

```json
{
  "kernel": {
    "enabled": true,
    "command": ["lattice-kernel", "analyze"],
    "policy": "kernel/policy.json"
  }
}
```

## 6. Inspect

```bash
ps aux | rg lattice-netcat
cat my-board/state/traces/trace.log
```
