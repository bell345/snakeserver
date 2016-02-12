#!/usr/bin/env python3

import re
from datetime import datetime

def determine_status_codes():
    try:
        from http import HTTPStatus as status_codes
    except ImportError:
        try:
            import http.client as status_codes
        except ImportError:
            status_codes = None

    if status_codes is None:
        status_codes = {}
        _SEP_RE = re.compile(r'[ \-]')
        for code, desc in HTTP_CODES.items():
            key = "_".join(_SEP_RE.split(desc.upper()))
            setattr(status_codes, key, code)

        return status_codes
    else:
        return status_codes


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
NEWLINE_RE     = re.compile(rb'\r?\n')
BLANK_LINE_RE  = re.compile(rb'\r?\n\r?\n')
COMMA_RE       = re.compile(r', *')
SEMICOLON_RE   = re.compile(r'; *')

codes = determine_status_codes()

class ProtocolError(Exception):
    pass

class ResponseError(Exception):
    def handler(self, req, res):
        return True

class HTTPError(ResponseError):

    def __init__(self, code, message=None):
        self.code = code
        self.message = message

    def handler(self, req, res):
        res.status(self.code).send(self.message or None)
        return True

    def __repr__(self):
        return "<HTTPError {}: {}>".format(self.code, HTTP_CODES.get(self.code, "Error Code Not Implemented"))

# RFC 7231 compliant!
class HTTPNegotiation:

    @staticmethod
    def parse_value(value):
        val, *params = SEMICOLON_RE.split(value)
        q = 1.0
        for v in params:
            p,v = v.split("=")
            if p != "q":
                val += ";{}={}".format(p, v)
            else:
                q = float(v[:5])

        return val, q

    empty = False
    missing = False
    def __init__(self, value):
        if value == "":
            self.empty = True
            return
        elif value is None:
            self.empty = True
            self.missing = True
            return

        self.values = []
        fields = COMMA_RE.split(value)
        for f in fields:
            self.values.append(HTTPNegotiation.parse_value(f))

    def negotiate(self, values):
        values = list(filter(lambda v: v and self[v] != 0.0, values))
        if not values: return None
        return max(values, key=lambda v: self[v])

    def __iter__(self):
        return self.values

    def __getitem__(self, item):
        if self.empty:
            return 1.0

        if item in self:
            for v,q in self.values:
                if v == item:
                    return q

        if ";" in item:
            base, *params = item.split(";")
            if base in item:
                return self[base]

        if "/" in item:
            group, *_ = item.split("/")
            group += "/*"
            if group in self:
                return self[group]
            elif "*/*" in self:
                return self["*/*"]

        if "*" in self:
            return self["*"]

        return 0.0

    def __contains__(self, item):
        for v,q in self.values:
            if v == item:
                return True

        return False

    def __bool__(self):
        return not self.missing


def htmltime(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

def fromhtmltime(s):
    return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S GMT")
