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
        while True:
            try:
                req = Request(self)
            except ProtocolError:
                break
            except (BrokenPipeError, OSError, socket.timeout) as e:
                print(e, file=sys.stderr)
                break

            if not req: break
            print("recv <{}:{}>: {}".format(self.addr[0], self.addr[1], str(req)))
            res = req.response

            try:
                if req.method in ("GET", "HEAD"):
                    static_prefix = "/srv/http/80"
                    static_path = os.path.join(*urlparse(req.fullpath).path.split("/"))
                    path = os.path.join(static_prefix, static_path)

                    if os.path.isdir(path):
                        for poss in ["index.html", "index.htm", ""]:
                            newpath = os.path.join(path, poss)
                            if os.path.isfile(newpath):
                                path = newpath

                    if not os.path.isfile(path):
                        res.status(codes.NOT_FOUND).send()
                        break

                    mime, encoding = mimetypes.guess_type(path)
                    modtime = datetime.fromtimestamp(int(os.path.getmtime(path)))
                    res.set("Last-Modified", htmltime(modtime))

                    if req.get("If-Modified-Since"):
                        expect = fromhtmltime(req.get("If-Modified-Since"))
                        if expect >= modtime:
                            res.status(codes.NOT_MODIFIED).send()
                            break

                    res.set("Content-Type", mime)
                    if req.method == "GET":
                        with open(path, "rb") as fp:
                            success = res.send(fp.read())
                            if not success: break
                    else:
                        res.send()

                    # TODO: replace with proper implementation
                    #msg = "Hello, world!\r\n"
                    #success = res.send(msg)
                    #if not success: break
                else:
                    res.status(codes.NOT_IMPLEMENTED).set("Allow", "GET").send()
                    break

                if req.headers.get("Connection", "").lower() == "close":
                    break
                if req.headers.get("Connection", "").lower() == "keep-alive":
                    self.conn.settimeout(None)

            except (ProtocolError, BrokenPipeError, OSError, socket.timeout) as e:
                print(e, file=sys.stderr)
                break

            if self.closed: break

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
