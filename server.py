#!/usr/bin/env python3

import socket
import threading

from util import *
from connection import HTTPConnection

class TCPServer:

    closed = False
    def __init__(self, config):
        self.config = config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []
        self.thread = threading.Thread(target=self._worker)
        self.thread.start()
        print("Started server")

    def _worker(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.config.get("host", ""), self.config.get("port", 80)))
        self.sock.listen(self.config.get("max_connections", 32))

        while True:
            conn, addr = self.sock.accept()

            if len(self.connections) < self.config.get("max_connections", 32):
                self.connections.append(HTTPConnection(self, (conn, addr)))
                print("open <{}:{}>: ({} total)".format(addr[0], addr[1], len(self.connections)))
            else:
                try:
                    code = codes.SERVICE_UNAVAILABLE
                    conn.sendall("HTTP/1.1 {} {}\r\n\r\n".format(code, HTTP_CODES.get(code, "")).encode("ascii"))
                    conn.close()
                except (BrokenPipeError, OSError, socket.timeout):
                    pass


    def close(self):
        if not self.closed:
            for conn in self.connections:
                if conn: conn.close()
            self.sock.close()
            self.closed = True

    def __bool__(self):
        return not self.closed
