# Quick Start

```bash
# Validate
./lattice validate examples/simple-board

# Run one tick
./lattice run examples/simple-board --once

# Inspect traces
./trace-resolve examples/simple-board/state/traces/trace.log -v
```

Try the netcat projection example:

```bash
./lattice run examples/netcat-board --once
```

TCP echo test:

```bash
echo "hello" | ./lattice-netcat 127.0.0.1 9999
```
