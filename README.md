# snakeserver

A toy implementation of a multi-threaded static HTTP server in Python.

## Running

Snakeserver is a program that no longer requires command-line arguments to be
run. All configuration is facilitated by a single paramter, the `-c` or
`--config` parameter, which specifies the path to a JSON configuration file. A
set of defaults has been provided for my own use, but this configuration will
be needed to get more than a few predetermined locations.

Run the program through the `python3` interpreter
(`python3 path/to/snakeserver` -c <config file destination>).

## Configuration

As mentioned, the program uses a JSON formatted configuration file. There are
multiple levels in the file, but each level inherits the properties of its 
parent unless overridden. Every one of these properties can be specified
at any level, lower levels of course overriding their parents and defaults.
The values only get read at certain levels of the parse tree, however.
The following is a brief rundown of the configuration format.

*All the properties are read at the server level unless specified.*

#### `max_connections`
This represents the maximum number of simultaneous connections for each TCP 
server you specify. Defaults to 32.

#### `timeout`
For each new connection made, this is the number of seconds the server will
wait for an inital request. After which the socket will timeout and become
available. Defaults to 15 seconds.

#### `default_type`
If the python `mimetypes` module fails to find a suitable MIME type for the
object on the server being requested, this is the MIME type sent instead.
Defaults to 'application/octet-stream'. This option doesn't really need to
be changed.

#### `charset`
Default charset for server resources. Defaults to 'utf-8'.

#### `gzip`
A boolean variable for whether or not the server should use GZIP compression
when acceptable. Defaults to true.

#### `index`
An array of filenames which will be tested for existence, then served if a 
directory is requested without a filename. Defaults to 
`['index.html', 'index.htm']`.

#### `servers (top level)`
An array of objects representing each server the program should open for new 
connections. The default serves `localhost:8086` with the contents of 
`/srv/http/80` and `localhost:8000` with the contents of `/srv/http/81`.

#### `port`
The port that the server will listen on for new connections. Defaults to 80.

#### `host`
The host that the server will listen on for new connections. Defaults to 
`''` (empty string), a symbolic constant for all local interfaces.

#### `ipv6`
A boolean variable indicating whether or not the server should listen using
IPV6 instead of IPV4. Defaults to false.

#### `locations`
A dictionary of path mappings to objects representing a single route the
request can be matched to, in a similar way to [express](express.js).

#### `root (route level)`
The only thing a route can do right now using this configuration is serve
statically from this location on the filesystem. Make sure the server's
running process has read permissions!

## Extensibility

This small Python HTTP server was not really designed for interoperability
or dynamism. For dynamic serving of web pages, you're probably better
off using something like [django](django). However, adding an importable
interface would be a fun activity in server-side scripting and maintaning
a public API.

[express]: http://expressjs.com/
[django]: https://www.djangoproject.com/