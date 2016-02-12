#!/usr/bin/env python3

import os
import sys
import socket
import mimetypes
mimetypes.init()
from urllib.parse import urlparse

from util import *

PARAM_RE      = re.compile(r':([^:/]+)')
PARAM_SUB     = r'(?P\1[^/]+)'
RE_ESCAPE_RE  = re.compile(r'[\-\.]')
RE_ESCAPE_SUB = r'\\\1'
SLASH_RE      = re.compile(r'/')
EMPTY_RE      = re.compile(r'')

def path_to_regexp(s):
    parts = []
    for part in SLASH_RE.split(s):
        part = RE_ESCAPE_RE.sub(RE_ESCAPE_SUB, part)
        part = PARAM_RE.sub(PARAM_SUB, part)
        parts.append(part)

    return re.compile("^/?" + "/".join(parts))

def static(static_prefix):
    def handle(req, res):
        if req.method in ("GET", "HEAD"):
            static_path = os.path.join(*urlparse(req.path).path.split("/"))
            path = os.path.join(static_prefix, static_path)

            if os.path.isdir(path):
                if not req.fullpath.endswith("/"):
                    res.redirect(req.fullpath + "/")
                    return

                for poss in req.config.get("index", ["index.html", "index.htm"]):
                    newpath = os.path.join(path, poss)
                    if os.path.isfile(newpath):
                        path = newpath

            if not os.path.isfile(path):
                return True

            res.send_file(path)
        else:
            res.set("Allow", "GET, HEAD")
            raise HTTPError(codes.METHOD_NOT_ALLOWED)

    return handle

def not_found(req, res):
    raise HTTPError(codes.NOT_FOUND)

class Route:

    def __init__(self, method, pattern, f):
        self.method = method
        if pattern is None:
            self.pattern = EMPTY_RE
        elif type(pattern) == str:
            self.pattern = path_to_regexp(pattern)
        else:
            self.pattern = pattern

        self.func = f

    def matches(self, req):
        if self.method is not None and req.method != self.method:
            return False

        return self.pattern.search(req.fullpath) != -1

    def __call__(self, req, res):
        m = self.pattern.match(req.path or req.fullpath)
        if not m:
            return True
        req.base = (req.base or "") + m.string[m.start():m.end()]
        req.path = m.string[m.end():]
        return self.func(req, res)

HTTP_METHODS = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "HEAD",
    "OPTIONS"
]

class Router:

    stack = []
    error_handlers = []
    def __init__(self):
        def _method_gen(method):
            def method_use(self, path, f=None):
                if not f:
                    f = path
                    path = None

                self.stack.append(Route(method, path, f))
                return self

            return method_use

        for method in HTTP_METHODS:
            setattr(self, method.lower(), _method_gen(method))

    def use(self, path, f=None):
        if not f:
            f = path
            path = None

        self.stack.append(Route(None, path, f))
        return self

    def all(self, *args, **kwargs):
        return self.use(*args, **kwargs)

    def handler(self, f):
        self.error_handlers.append(f)

    def __call__(self, req, res):

        if req.headers.get("Connection", "").lower() == "close":
            res.set("Connection", "close")
        if req.headers.get("Connection", "").lower() == "keep-alive":
            req.conn.settimeout(None)
            res.set("Connection", "keep-alive")

        matches = [r for r in self.stack if r.matches(req)]

        try:
            if req.method not in HTTP_METHODS:
                res.set("Allow", ", ".join(HTTP_METHODS))
                raise HTTPError(codes.NOT_IMPLEMENTED)

            for match in matches:
                if not match(req, res):
                    break

        except (ProtocolError, BrokenPipeError, OSError, socket.timeout) as e:
            print(e, file=sys.stderr)
            return True

        except ResponseError as e:
            try:
                if e.handler(req, res):
                    for handler in self.error_handlers:
                        if not handler(e, req, res):
                            break

            except (ProtocolError, BrokenPipeError, OSError, socket.timeout) as e:
                print(e, file=sys.stderr)

            finally:
                return True


        if req.headers.get("Connection", "").lower() == "close":
            return True
