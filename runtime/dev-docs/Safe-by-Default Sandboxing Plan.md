# Safe-by-Default Sandboxing Plan

This plan describes POSIX-native safety for FIFO-first boards.

## The Problem

Without constraints, a port path could target system files:

```json
{
  "name": "dangerous",
  "direction": "in",
  "path": "/etc/passwd"
}
```

## The Solution: Three-Layer Defense

### Layer 1: Substrate Root

Default all relative paths into a project-local substrate:

```
BOARD/
  board.json
  .lattice/
    fifos/
    traces/
  state/  # optional symlink
```

### Layer 2: System Blocklist

Reject paths that resolve inside system directories (`/etc`, `/usr`, `/bin`, etc).

### Layer 3: Namespaces (Linux)

Use `unshare` or containerization where available.

## Implementation Outline

### Schema

```json
{
  "node_id": "local",
  "substrate": {
    "root": ".lattice",
    "allow_absolute": false,
    "custom_blocklist": []
  },
  "ports": [
    {"name": "input", "direction": "in", "path": "fifos/input.fifo"}
  ],
  "transports": []
}
```

### Path Resolution

```python
def _safe_path(board_path: str, user_path: str) -> str:
    substrate = Path(board_path) / ".lattice"
    if os.path.isabs(user_path):
        if not os.getenv("LATTICE_ALLOW_ABSOLUTE"):
            raise ValueError(f"Absolute paths forbidden: {user_path}")
        return user_path
    safe = (substrate / user_path).resolve()
    if not safe.is_relative_to(substrate):
        raise ValueError(f"Path escape attempt: {user_path}")
    return str(safe)
```

## Notes

- FIFO-first ports are the structural anchor.
- Transports attach to FIFOs and never define paths.
