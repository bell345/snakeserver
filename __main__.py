#!/usr/bin/env python3

import sys
import json
import atexit
import argparse

__version__ = (0, 5, 1)
__version_info__ = ".".join(map(str, __version__))

APP_NAME = "snakeserver"
APP_AUTHOR = "bell345"
APP_VERSION = __version_info__
PYTHON_VERSION = ".".join(map(str, sys.version_info[:3]))

DEFAULT_CONFIG = {
    'max_connections': 64,
    'timeout': 15,
    'default_type': "application/octet-stream",
    "charset": "utf-8",
    "gzip": True,
    "index": ["index.html", "index.htm"],
    'servers': [
        {
            "port": 8086,
            "locations": {
                "/": {
                    "root": "/srv/http/80"
                }
            }
        },
        {
            "port": 8000,
            "locations": {
                "/": {
                    "root": "/srv/http/81"
                }
            }
        }
    ]
}

from server import TCPServer

servers = []
def cleanup():
    for server in servers:
        if server: server.close()

atexit.register(cleanup)

def main():

    parser = argparse.ArgumentParser(prog=APP_NAME,
            description="A lightweight multithreaded HTTP server written in Python.",
            epilog="(C) Thomas Bell 2016, MIT License.")
    parser.add_argument("--version", action="version", version=APP_VERSION)

    parser.add_argument("-c", "--config", default=None, type=argparse.FileType('r'),
            help="The JSON formatted server configuration file.")
    args = parser.parse_args()

    try:
        config = DEFAULT_CONFIG
        if args.config:
            config.update(json.load(args.config))

        for conf in config.get("servers", []):
            conf.update(config)
            servers.append(TCPServer(conf))

    except (KeyboardInterrupt, SystemExit, Exception) as e:
        print(e, file=sys.stderr)

    except (ValueError, KeyError) as e:
        print("Error parsing configuration: {}".format(e), file=sys.stderr)

if __name__ == "__main__":
    main()
