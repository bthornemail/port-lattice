# Lattice Runtime Tutorial

This tutorial walks through creating and running a FIFO-first POSIX lattice.

## Part 1: Simple FIFO Pipeline

### Create the Board

```bash
# Create directory structure
mkdir -p my-first-lattice/state/sockets

# Create board definition
cat > my-first-lattice/board.json <<'EOF'
{
  "node_id": "tutorial",
  "socket_dir": "state/sockets",
  "ports": [
    {
      "name": "input",
      "direction": "in"
    },
    {
      "name": "output",
      "direction": "out"
    }
  ],
  "transports": [],
  "procs": [
    {
      "name": "echo-worker",
      "command": "cat $LATTICE_PORT_INPUT > $LATTICE_PORT_OUTPUT",
      "waits": ["input"],
      "fires": ["output"],
      "env": {}
    }
  ],
  "health": {
    "tick_seconds": 2,
    "restart_delay": 1
  }
}
EOF
```

### Validate and Run

```bash
lattice validate my-first-lattice
lattice run my-first-lattice
```

### Test the Pipeline

In a second terminal:

```bash
echo "Hello, Lattice!" > my-first-lattice/state/sockets/input.fifo &
cat my-first-lattice/state/sockets/output.fifo
```

## Part 2: Drop-in Ports and Transports

```bash
mkdir -p my-first-lattice/{ports.d,transports.d}

cat > my-first-lattice/ports.d/log.json <<'EOF'
{
  "name": "log",
  "direction": "out"
}
EOF

cat > my-first-lattice/transports.d/log-tcp.json <<'EOF'
{
  "name": "log-tcp",
  "kind": "netcat",
  "attach": "log",
  "spec": {
    "protocol": "tcp",
    "mode": "connect",
    "host": "127.0.0.1",
    "port": 5555
  }
}
EOF
```

The running lattice will pick up the changes on the next tick.

## Part 3: Netcat Listener Projection

```bash
mkdir -p netcat-demo/{ports.d,transports.d,state/sockets}

cat > netcat-demo/board.json <<'EOF'
{
  "node_id": "netcat-demo",
  "socket_dir": "state/sockets",
  "ports": [
    {"name": "tcp-echo", "direction": "inout"}
  ],
  "transports": [
    {
      "name": "tcp-listener",
      "kind": "netcat",
      "attach": "tcp-echo",
      "spec": {
        "protocol": "tcp",
        "mode": "listen",
        "port": 9999,
        "keep_open": true,
        "exec": "/bin/cat"
      }
    }
  ],
  "procs": [],
  "health": {"tick_seconds": 2, "restart_delay": 1}
}
EOF

lattice run netcat-demo --once
```

Test:

```bash
echo "hello" | lattice-netcat 127.0.0.1 9999
```

## Part 4: Self-Healing Demonstration

1. Run `lattice run examples/netcat-board`.
2. Kill the netcat process.
3. Watch the runtime restart it on the next tick.

Check health state in `examples/netcat-board/state/health.json`.

## Part 5: Kernel Gate (Optional)

```bash
cat > my-first-lattice/kernel-policy.json <<'EOF'
{
  "max_components": 1,
  "max_radius": 10
}
EOF
```

Add to `board.json`:

```json
{
  "kernel": {
    "enabled": true,
    "command": ["lattice-kernel", "analyze"],
    "policy": "kernel-policy.json"
  }
}
```
