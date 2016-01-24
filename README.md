# snakeserver

A toy implementation of a multi-threaded static HTTP server in Python.

## Running

Snakeserver is a command-line driven program, with a few interesting options to
choose from. Run the project through the `python` interpreter
(`python /path/to/snakeserver)`). The command line arguments are as follows:

    usage: snakeserver [-h] [--version] [-p PORT] [-H HOST] [-c CONNECTIONS]
                    [-t TIMEOUT]

    A lightweight multithreaded HTTP server written in Python.

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      -p PORT, --port PORT  A port to listen on for connections. Defaults to port
                            8086.
      -H HOST, --host HOST  A hostname or IP address where the server will listen
                            for connections. Defaults to local interfaces.
      -c CONNECTIONS, --connections CONNECTIONS
                            The maximum number of connections the server will
                            handle concurrently. Defaults to 10.
      -t TIMEOUT, --timeout TIMEOUT
                            The timeout period for new connections in seconds.
                            Defaults to 15 seconds.

