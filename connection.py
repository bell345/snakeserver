#!/usr/bin/env python3

import threading

from util import *
from request import Request
from router import Router, static, not_found

class HTTPConnection:
    """A class that handles a single HTTP conversation to a TCP client.

    Supports sending and receiving well-formed messages in the event of success or failure.
    """

    closed = False
    def __init__(self, server, conn_info):
        self.server = server
        self.config = server.config
        self.conn, self.addr = conn_info
        self.conn.settimeout(self.config.get("timeout") or 15)

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        router = Router()

        for mountpoint, conf in self.config.get("locations", {}).items():
            conf.update(self.config)
            router.use(mountpoint, static(conf.get("root")))

        for code, page in self.config.get("error_pages", {}).items():
            def handler(err, req, res):
                if type(err) == HTTPError and err.code == code:
                    res.send_file(page)
                else: return True
            router.handler(handler)

        router.use(not_found)

        while True:
            req = Request(self)
            if not req or self.closed: break

            err = router(req, req.response)
            if err: break

        return self.close()

    def close(self):
        if not self.closed:
            self.closed = True
            self.server.connections = [s for s in self.server.connections if s]
            print("term <{}:{}>: ({} left)".format(self.addr[0], self.addr[1], len(self.server.connections)))
            self.conn.close()

    def __bool__(self):
        return not self.closed
