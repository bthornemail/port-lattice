#!/usr/bin/env python3
import socket
import time

while True:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    sock.sendto(b"ping udp\n", ("127.0.0.1", 9994))
    try:
        data, _ = sock.recvfrom(2048)
        with open("/tmp/lattice-udp.out", "wb") as f:
            f.write(data)
    except Exception:
        with open("/tmp/lattice-udp.out", "wb") as f:
            f.write(b"no response\n")
    sock.close()
    time.sleep(2)
