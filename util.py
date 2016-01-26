#!/usr/bin/env python3

import re
from datetime import datetime
from http import HTTPStatus as codes

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

class ResponseError(Exception):
    pass

class HTTPError(ResponseError):

    def __init__(self, code, message=None):
        self.code = code
        self.message = message

    def handler(self, req, res):
        res.status(self.code).send()
        return True

    def __repr__(self):
        return "<HTTPError {}: {}>".format(self.code, HTTP_CODES.get(self.code, "Error Code Not Implemented"))

def htmltime(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

def fromhtmltime(s):
    return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S GMT")
