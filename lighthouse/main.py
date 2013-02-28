#! /usr/bin/python
# Copyright (c) 2012, 2013 Viliam Holub, Logentries

"""

Logentries Lighthouse

"""

# System imports
import getopt
import sys
import logging

# Local imports
import data
import server
import sync

from __init__ import __version__
from __init__ import SERVER_NAME

# Server version string
VERSION_INFO = SERVER_NAME +" Version " +__version__

# Usage help
USAGE = """
--help      prints help and exits
--version   prints version information and exits
--data.d    path to configuration files
--port=     port we listen on
--seeds=    other instances in the cluster, comma-separated
"""

# Exit codes
EXIT_OK = 0   # OK
EXIT_HELP = 1 # Help text printed
EXIT_ERR = 2  # Error

# Log entry format
LOG_FORMAT = "%(asctime)s.%(msecs)d %(name)-10s %(levelname)-8s %(message)s"


def die(cause, exit_code=EXIT_ERR):
	""" Print the text given and exits. """
	print >>sys.stderr, cause
	sys.exit( exit_code)


def print_usage( version_only=False):
	""" Prints usage info with version. """
	print >>sys.stderr, VERSION_INFO
	if not version_only:
		print >>sys.stderr, USAGE

	sys.exit( EXIT_HELP)


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
	try:
		optlist, args = getopt.gnu_getopt( sys.argv[1:], '', 'help version data.d= port= seeds='.split())
	except getopt.GetoptError, err:
		die( 'Parameter error: ' +str( err))
	port = 8001
	for name, value in optlist:
		if name == "--help":
			print_usage()
		if name == "--version":
			print_usage( True)
		if name == "--data.d":
			data.set_data_dir( value)
		if name == "--port":
			port = int( value)
		if name == "--seeds":
			seeds = value.split( ',')
			for seed in seeds:
				r = sync.cluster_state.add_instance( seed)
				if not r:
					die( 'Invalid seed %s'%seed)
	data.load_data()

	sync.init_cluster_state( 'this IP:port') #XXX

	server.run( port=port)

