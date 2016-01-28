#!/usr/bin/env python3

import os
import mimetypes
mimetypes.init()
from datetime import datetime

from __main__ import APP_NAME, APP_VERSION, PYTHON_VERSION
from util import *

class Response:

    def __init__(self, req):
        self.server = req.server
        self.config = req.config
        self.request = req
        self.conn = req.conn
        self.addr = req.addr
        self.headers = {}
        self.status_sent = False
        self.headers_sent = False
        self.body_sent = False

    def status(self, code):
        if self.status_sent:
            raise ProtocolError("The status code has already been sent!")

        self.status_code = code
        self.status_message = HTTP_CODES.get(code, "Unimplemented Status Code")
        status_line = "HTTP/{} {} {}\r\n".format(
            self.request.version, self.status_code, self.status_message).encode("ascii")
        success = self.write(status_line)

        print("send <{}:{}>: {}".format(self.addr[0], self.addr[1], status_line.decode("ascii").strip("\r\n"), repr(self.request)))

        if success:
            self.status_sent = True
        return self

    def write(self, msg):
        if type(msg) == str:
            msg = msg.encode(self.config.get("charset") or "utf-8")

        self.conn.sendall(msg)
        return len(msg)

    def write_head(self, code=None, headers={}):
        self.status_code = code or self.status_code
        self.headers.update(headers)

        if not self.status_sent:
            self.status(code)

        self.set_default("Server", "{}/{} python/{}".format(APP_NAME, APP_VERSION, PYTHON_VERSION))
        self.set_default("Date", htmltime(datetime.utcnow()))

        for key,value in self.headers.items():
            self.write("{}: {}\r\n".format(key, value))

        self.write("\r\n")
        self.headers_sent = True
        return self

    def set(self, *args):
        if len(args) == 1 and type(args[0]) == dict:
            for key,value in args[0].items():
                self.set(key, value)
        elif len(args) == 2:
            key, value = args
            if type(key) == bytes: key = key.decode("ascii")
            if type(value) == bytes: value = value.decode("ascii")

            self.headers[key] = value

        return self

    def set_default(self, key, value):
        if key not in self.headers:
            self.set(key, value)

    def send_chunk(self, payload):
        if not self.status_sent:
            self.status(codes.OK)

        if not self.headers_sent:
            self.set_default("Transfer-Encoding", "chunked")

            self.write_head()

        self.write(hex(len(payload)))
        self.write("\r\n")
        self.write(payload)
        self.write("\r\n")

    def send(self, payload=None):
        if self.body_sent:
            raise ProtocolError("The message has already been sent!")

        if not self.status_sent:
            self.status(codes.OK)

        if not self.headers_sent:
            if payload is not None:
                self.set_default("Content-Length", len(payload))
                self.set_default("Content-Type", "application/json" if type(payload) == dict else "text/plain")

            self.write_head()

        if payload is not None:
            if type(payload) == str:
                payload = payload.encode(self.config.get("encoding") or "utf-8")

            self.conn.sendall(payload)
            print("send <{}:{}>: {} {} bytes".format(
                self.addr[0], self.addr[1], self.headers.get("Content-Type"), self.headers.get("Content-Length")))

        self.body_sent = True
        return self

    def send_file(self, filename):
        mime, encoding = mimetypes.guess_type(filename)
        modtime = datetime.fromtimestamp(int(os.path.getmtime(filename)))
        self.set("Last-Modified", htmltime(modtime))

        if self.request.get("If-Modified-Since"):
            expect = fromhtmltime(self.request.get("If-Modified-Since"))
            if expect >= modtime:
                raise HTTPError(codes.NOT_MODIFIED)

        self.set("Content-Type", mime or self.config.get("default_type") or "application/octet-stream")

        encoding = None
        encodings = [None]
        if self.config.get("gzip"):
            encodings.append("gzip")

        if self.request.accept_encodings:
            encoding = self.request.accept_encodings.negotiate(encodings[::-1])
        elif self.request.version >= "1.1":
            encoding = encodings[-1]

        if encoding:
            self.set("Content-Encoding", encoding)

        if self.request.method == "GET":
            if encoding == "gzip":
                import gzip
                with open(filename, "rb") as fp:
                    self.send(gzip.compress(fp.read()))

            else:
                with open(filename, "rb") as fp:
                    self.send(fp.read())
        else:
            self.send()

    def redirect(self, location):
        self.set("Location", location)
        raise HTTPError(codes.MOVED_PERMANENTLY)

    def end(self):
        if not self.server.closed:
            self.server.close()

    def close(self):
        self.end()
