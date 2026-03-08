#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

src="$tmp/src.ndjson"
dst="$tmp/dst.ndjson"

printf '%s\n' \
  '{"namespace":"ulp.trace.test.v0","authority":{"kind":"direct","basis":[]},"meta":{"writer":"test","epoch":1,"gen":1},"payload":{"op":"advance_tick","delta":1}}' \
  '{"namespace":"ulp.trace.test.v0","authority":{"kind":"direct","basis":[]},"meta":{"writer":"test","epoch":1,"gen":1},"payload":{"op":"create_entity","eid":1,"etype":"node","owner_mask":15}}' \
  > "$src"

port=39123
"$ROOT/seam-transport" serve --port "$port" --file "$src" >/dev/null 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true; rm -rf "$tmp"' EXIT

# Give server a moment.
sleep 0.2

"$ROOT/seam-transport" pull --port "$port" --out "$dst" --local ""

cmp "$src" "$dst"
echo "ok seam-transport"

