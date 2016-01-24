#!/usr/bin/env python3

import sys
import socket
import atexit
import argparse

__version__ = (0, 3, 0)
__version_info__ = ".".join(map(str, __version__))

APP_NAME = "snakeserver"
APP_AUTHOR = "bell345"
APP_VERSION = __version_info__
PYTHON_VERSION = ".".join(map(str, sys.version_info[:3]))

from util import *
from server import open_server, servers

def main():

    sock = None
    def cleanup():
        if sock: sock.close()
        for server in servers:
            if server: server.close()

    atexit.register(cleanup)

    parser = argparse.ArgumentParser(prog=APP_NAME,
            description="A lightweight multithreaded HTTP server written in Python.",
            epilog="(C) Thomas Bell 2016, MIT License.")
    parser.add_argument("--version", action="version", version=APP_VERSION)

    parser.add_argument("-p", "--port", default=8086, type=int,
            help="A port to listen on for connections. Defaults to port 8086.")
    parser.add_argument("-H", "--host", default="",
            help="A hostname or IP address where the server will listen for connections. Defaults to local interfaces.")
    parser.add_argument("-c", "--connections", default=10,
            help="The maximum number of connections the server will handle concurrently. Defaults to 10.")
    parser.add_argument("-t", "--timeout", default=15, type=float,
            help="The timeout period for new connections in seconds. Defaults to 15 seconds.")
    args = parser.parse_args()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((args.host, args.port))
            sock.listen(args.connections)

            while True:
                conn, addr = sock.accept()

                if len(servers) < args.connections:
                    open_server(conn, addr, timeout=args.timeout)
                    print("open <{}:{}>: ({} total)".format(addr[0], addr[1], len(servers)))
                else:
                    try:
                        code = codes.SERVICE_UNAVAILABLE
                        conn.sendall("HTTP/1.1 {} {}\r\n\r\n".format(code, HTTP_CODES.get(code, "")).encode("ascii"))
                        conn.close()
                    except (BrokenPipeError, OSError, socket.timeout):
                        pass

    except (KeyboardInterrupt, SystemExit, Exception) as e:
        print(e, file=sys.stderr)

if __name__ == "__main__":
    main()
