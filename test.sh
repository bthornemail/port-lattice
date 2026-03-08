#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

(cd "$ROOT/netcat" && ./test-lattice-netcat.sh)
(cd "$ROOT/runtime" && ./test-lattice.sh)

echo "ok port-lattice"

