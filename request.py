#!/usr/bin/env python3

import socket
from urllib.parse import urlparse, unquote

from util import *
from response import Response

class Request:

    def __init__(self, server):
        self.server = server
        self.conn = server.conn
        self.addr = server.addr
        self.response = Response(self)
        self.method = None
        self.fullpath = None
        self.version = "1.0"
        self.raw = b''
        self.payload = b''
        self.host = ""
        self.port = -1
        self.headers = {}

        self.processed = False

        req = self._recv_request()
        if not req: return

        success = self._parse_headers(req)
        if not success: return

        if "Content-Length" in self.headers:
            success = self._recv_payload(self.headers)
            if self.get("Content-Length") != "0" and not success: return

        self.processed = True

    def get(self, key, default=None):
        if key in self.headers:
            return self.headers[key]
        else:
            return default

    def consume(self, until=None, max_length=-1, buffer_size=4096):
        buf = b''
        if type(until) in (bytes, str):
            until = re.compile(until)
        until_cond = lambda: not until or (not until.search(buf))
        len_cond = lambda: max_length == -1 or len(buf) < max_length

        while until_cond() and len_cond():
            try:
                new_data = self.conn.recv(buffer_size)
            except (BrokenPipeError, OSError, socket.timeout) as e:
                print(e, file=sys.stderr)
                return b''

            # print("Got data: {}".format(new_data)) # don't remove
            buf += new_data
            if not new_data or (max_length != -1 and len(new_data) < buffer_size):
                break

        return buf

    def _recv_request(self):
        req = self.consume(until=BLANK_LINE_RE)
        if not req: return None
        self.raw += req

        payload = b''
        if BLANK_LINE_RE.search(req):
            req, payload = BLANK_LINE_RE.split(req, 1)
        self.payload += payload

        return req

    def _recv_payload(self):
        try:
            content_length = int(self.get("Content-Length"))
        except ValueError:
            self.response.status(codes.BAD_REQUEST).send("Invalid Content-Length\r\n")
            self.server.close()
            return False

        new_data = self.consume(max_length=max(-1, content_length - len(payload)))
        self.raw += new_data
        self.payload += new_data

        if len(self.payload) < content_length:
            return False

        return True

    def _parse_headers(self, req):
        try:
            lines = NEWLINE_RE.split(req)

            self.method, self.fullpath, self.version = STATUS_LINE_RE.match(lines[0].decode("ascii")).groups()
            if not self.version:
                self.version = "1.0"

            urlparts = urlparse(self.fullpath)
            getpart = lambda name: unquote(getattr(urlparts, name))
            self.path, self.query, self.fragment = \
                getpart("path"), getpart("query"), getpart("fragment")

            self.headers = {}
            for line in lines[1:]:
                if not line: break
                key, value = re.split(rb': *', line, 1)
                self.headers[key.title().decode("ascii")] = value.decode("ascii")

            if self.version >= "1.1" and "Host" not in self.headers:
                self.response.status(codes.BAD_REQUEST).send("Host header required\r\n")
                self.server.close()
                return False

            host = self.headers.get("Host", ":".join(map(str, self.conn.getsockname())))
            if ":" not in host:
                host += ":80"

            self.host, self.port = host.split(":", 1)
            self.port = int(self.port)

            port_url = ":{}".format(self.port) if self.port != 80 else ""
            self.url = "http://" + self.host + port_url + self.fullpath

        except (IndexError, ValueError, UnicodeDecodeError, AttributeError) as e:
            self.response.status(codes.BAD_REQUEST).send("Malformed headers\r\n")
            self.server.close()
            return False

        return True

    def __str__(self):
        if self.method and self.fullpath:
            return "{} {} HTTP/{}".format(self.method, self.fullpath, self.version)
        else:
            return repr(self)

    def __repr__(self):
        props = {}
        if self.method: props["method"] = self.method
        if self.fullpath: props["fullpath"] = self.fullpath
        if self.host: props["host"] = "{}:{}".format(self.host, self.port)
        props["source"] = "{}:{}".format(*self.addr)

        props_str = ", ".join(map(lambda i: "{}={}".format(*i), props.items()))

        return "<Request {}>".format(props_str)

    def __bool__(self):
        return self.processed
