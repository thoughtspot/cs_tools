from __future__ import annotations

import socket


def _find_my_local_ip() -> str:
    """
    Gets the local ip, or loopback address if not found.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("10.255.255.255", 1))  # does not need to be a valid addr

        try:
            ip = sock.getsockname()[0]
        except IndexError:
            ip = "127.0.0.1"

    return ip
