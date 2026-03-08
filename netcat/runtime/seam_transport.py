#!/usr/bin/env python3
"""
Transport-only seam envelope mover for ULP NDJSON streams.

This is deliberately minimal:
- No authority logic.
- No merge logic.
- Anti-entropy hook = pull-by-digest (fetch if local digest differs).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Manifest:
    sha256_hex: str
    count: int


def _atomic_write_text(path: Path, text: str) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def compute_manifest(path: Path) -> Manifest:
    h = hashlib.sha256()
    count = 0
    with path.open("rb") as f:
        for line in f:
            if not line.strip():
                continue
            count += 1
            h.update(line)
    return Manifest(sha256_hex=h.hexdigest(), count=count)


def send_all(sock: socket.socket, data: bytes) -> None:
    view = memoryview(data)
    while view:
        n = sock.send(view)
        view = view[n:]


def recv_line(sock: socket.socket, limit: int = 4096) -> bytes:
    buf = bytearray()
    while len(buf) < limit:
        ch = sock.recv(1)
        if not ch:
            break
        buf += ch
        if ch == b"\n":
            break
    return bytes(buf)


def serve(host: str, port: int, ndjson_path: Path, write_port_path: Path | None) -> int:
    ndjson_path = ndjson_path.resolve()
    if not ndjson_path.exists():
        print(f"missing file: {ndjson_path}", file=sys.stderr)
        return 2

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(16)
        actual_port = s.getsockname()[1]
        if write_port_path is not None:
            _atomic_write_text(write_port_path, f"{actual_port}\n")
        print(f"seam-transport: serving {ndjson_path} on {host}:{actual_port}", file=sys.stderr)

        while True:
            conn, addr = s.accept()
            with conn:
                try:
                    mf = compute_manifest(ndjson_path)
                    header = f"MANIFEST sha256:{mf.sha256_hex} count={mf.count}\n".encode("utf-8")
                    send_all(conn, header)
                    cmd = recv_line(conn).strip().upper()
                    if cmd == b"GET":
                        send_all(conn, ndjson_path.read_bytes())
                    # Anything else is NOOP.
                except Exception as e:
                    print(f"seam-transport: error serving {addr}: {e}", file=sys.stderr)
    return 0


def pull(host: str, port: int, out_path: Path, local_path: Path | None) -> int:
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    local_mf: Manifest | None = None
    if local_path is not None and local_path.exists():
        local_mf = compute_manifest(local_path.resolve())

    with socket.create_connection((host, port), timeout=10) as sock:
        header = recv_line(sock)
        if header == b"":
            print("unexpected header: b'' (server closed connection)", file=sys.stderr)
            return 2
        if not header.startswith(b"MANIFEST "):
            print(f"unexpected header: {header!r}", file=sys.stderr)
            return 2
        parts = header.decode("utf-8", errors="replace").strip().split()
        # MANIFEST sha256:<hex> count=<n>
        remote_hash = parts[1].split("sha256:", 1)[-1]
        remote_count = int(parts[2].split("count=", 1)[-1])
        remote_mf = Manifest(sha256_hex=remote_hash, count=remote_count)

        if local_mf is not None and local_mf == remote_mf:
            send_all(sock, b"NOOP\n")
            print("up-to-date", file=sys.stderr)
            return 0

        send_all(sock, b"GET\n")
        data = sock.recv(1024 * 1024)
        chunks = [data]
        while data:
            data = sock.recv(1024 * 1024)
            if data:
                chunks.append(data)
        out_path.write_bytes(b"".join(chunks))

    got = compute_manifest(out_path)
    if got != remote_mf:
        print(
            f"manifest mismatch after pull: expected sha256:{remote_mf.sha256_hex} count={remote_mf.count} "
            f"got sha256:{got.sha256_hex} count={got.count}",
            file=sys.stderr,
        )
        return 3
    print("ok", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Transport-only seam envelope mover (NDJSON).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("serve", help="Serve an NDJSON file over a minimal manifest+GET protocol.")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, required=True, help="Port to bind. Use 0 to request an OS-assigned port.")
    sp.add_argument("--file", required=True)
    sp.add_argument(
        "--write-port",
        default="",
        help="If set, write the bound port number to this file (useful when --port=0).",
    )

    pp = sub.add_parser("pull", help="Pull NDJSON file from server if digest differs.")
    pp.add_argument("--host", default="127.0.0.1")
    pp.add_argument("--port", type=int, required=True)
    pp.add_argument("--out", required=True)
    pp.add_argument("--local", default="")

    args = ap.parse_args()

    if args.cmd == "serve":
        write_port = Path(args.write_port) if args.write_port else None
        return serve(args.host, args.port, Path(args.file), write_port)
    if args.cmd == "pull":
        local = Path(args.local) if args.local else None
        return pull(args.host, args.port, Path(args.out), local)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
