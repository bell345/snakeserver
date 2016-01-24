#!/usr/bin/env python3

from __main__ import APP_NAME, APP_VERSION, PYTHON_VERSION
from util import *

class Response:

    def __init__(self, req):
        self.server = req.server
        self.request = req
        self.conn = req.conn
        self.addr = req.addr
        self.headers = {}
        self.status_sent = False
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
            msg = msg.encode()

        self.conn.sendall(msg)
        return True

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

    def send(self, payload=None):
        if not self.status_sent:
            self.status(codes.OK)

        if self.body_sent:
            raise ProtocolError("The message has already been sent!")

        def set_default(header, val):
            if header not in self.headers:
                self.set(header, val)

        set_default("Server", "{}/{} python/{}".format(APP_NAME, APP_VERSION, PYTHON_VERSION))
        set_default("Date", htmltime(datetime.utcnow()))
        if payload is not None:
            set_default("Content-Length", len(payload))
            set_default("Content-Type", "application/json" if type(payload) == dict else "text/plain")

        for key,value in self.headers.items():
            self.write("{}: {}\r\n".format(key, value))

        self.write("\r\n")

        if payload is not None:
            if type(payload) == str:
                payload = payload.encode("utf-8")

            self.conn.sendall(payload)
            print("send <{}:{}>: {} {} bytes".format(
                self.addr[0], self.addr[1], self.headers.get("Content-Type"), self.headers.get("Content-Length")))

        self.body_sent = True
        return self


    def end(self):
        if not self.server.closed:
            self.server.close()
