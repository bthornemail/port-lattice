#!/usr/bin/env python3
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 9994))

while True:
    data, addr = sock.recvfrom(2048)
    if not data:
        continue
    sock.sendto(data, addr)
