#!/usr/bin/env python3

import re
import os
import sys
import socket
import atexit
import argparse
import mimetypes
mimetypes.init()
import threading
from time import sleep
from datetime import datetime
from urllib.parse import urlparse, urlunparse, quote, unquote
from http import HTTPStatus as codes

__version__ = (0, 2, 0)
__version_info__ = ".".join(map(str, __version__))

APP_NAME = "snakeserver"
APP_AUTHOR = "bell345"
APP_VERSION = __version_info__
PYTHON_VERSION = ".".join(map(str, sys.version_info[:3]))

HTTP_CODES = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Payload Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    416: "Range Not Satisfiable",
    417: "Expectation Failed",
    426: "Upgrade Required",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported"
}
STATUS_LINE_RE = re.compile(r'^([A-Z]+) ([^\x00-\x20<>#%"]+)(?: HTTP/([0-9A-Za-z.]+))?$')
NEWLINE_RE = re.compile(rb'\r?\n')
BLANK_LINE_RE = re.compile(rb'\r?\n\r?\n')

class ProtocolError(Exception):
    pass

servers = []

def htmltime(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

def fromhtmltime(s):
    return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S GMT")

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

class Route:
    @staticmethod
    def static(req, res, next):
        pass

    def __init__(self, method, spec, func):
        spec = spec.lstrip("/")
        self.method = method
        self.path = spec.split("/")


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
                if req.method == "GET":
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

                    with open(path, "rb") as fp:
                        res.set("Content-Type", mime)
                        success = res.send(fp.read())
                        if not success: break

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

sock = None
def cleanup():
    if sock: sock.close()
    for server in servers:
        if server: server.close()

atexit.register(cleanup)

def main():
    global servers

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
                    servers.append(HTTPServer(conn, addr, timeout=args.timeout))
                    print("open <{}:{}>: ({} total)".format(*addr, len(servers)))
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
