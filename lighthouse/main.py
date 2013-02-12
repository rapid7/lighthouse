#! /usr/bin/python
# Copyright (c) 2012 Viliam Holub, Logentries

"""

Logentries Lighthouse



GET commands are safe
PUT, DELETE commands on update are idempotent
All commands are atomic


"""

import getopt
import sys
import logging

import data
import server
import sync
import state

from __init__ import __version__
from __init__ import SERVER_NAME

VERSION_INFO = SERVER_NAME +" Version " +__version__

USAGE = """
--help     prints help and exits
--version  prints version information and exits
"""

# Exit codes
EXIT_OK = 0
EXIT_HELP = 1
EXIT_ERR = 2



def die(cause, exit_code=EXIT_ERR):
	print >>sys.stderr, cause
	sys.exit( exit_code)


def print_usage( version_only=False):
	print >>sys.stderr, VERSION_INFO
	if not version_only:
		print >>sys.stderr, USAGE

	sys.exit( EXIT_HELP)


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG, format="%(asctime)s.%(msecs)d %(name)-10s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
	try:
		optlist, args = getopt.gnu_getopt( sys.argv[1:], '', 'help version data.d= port= servers='.split())
	except getopt.GetoptError, err:
		die( "Parameter error: " +str( err))
	data_dir = None
	port = 8001
	for name, value in optlist:
		if name == "--help":
			print_usage()
		if name == "--version":
			print_usage( True)
		if name == "--data.d":
			data_dir = value
		if name == "--port":
			port = int(value)
		if name == "--servers":
			servers = value.split(',')
			sync.add_servers(servers)
	sync.start()
	server.run( data_dir=data_dir, port=port)
	sync.stop()
