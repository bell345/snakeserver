#!/usr/bin/env python3

import os
import socket
import threading
import mimetypes
mimetypes.init()
from datetime import datetime
from urllib.parse import urlparse

from util import *
from request import Request
from router import Router, static, not_found

servers = []

def open_server(*args, **kwargs):
    servers.append(HTTPServer(*args, **kwargs))

class HTTPServer:
    """A class that handles a single HTTP conversation to a TCP client.

    Supports sending and receiving well-formed messages in the event of success or failure.
    """

    closed = False
    def __init__(self, conn, addr, timeout=None):
        conn.settimeout(timeout)
        self.conn = conn
        self.addr = addr
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        router = Router()
        router.use(static("/srv/http/80"))
        router.use(not_found)

        while True:
            try:
                req = Request(self)
            except ProtocolError:
                break
            except (BrokenPipeError, OSError, socket.timeout) as e:
                print(e, file=sys.stderr)
                break

            if not req or self.closed: break

            err = router(req, req.response)
            if err: break

        return self.close()

    def close(self):
        global servers
        if not self.closed:
            self.closed = True
            servers = [s for s in servers if s]
            print("term <{}:{}>: ({} left)".format(self.addr[0], self.addr[1], len(servers)))
            self.conn.close()

    def __bool__(self):
        return not self.closed
