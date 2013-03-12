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
import server
import sync
import config
import helpers

from __init__ import __version__
from __init__ import SERVER_NAME

# Server version string
VERSION_INFO = SERVER_NAME +" Version " +__version__

# Usage help
USAGE = """
--help      prints help and exits
--version   prints version information and exits
--data.d    path to configuration files
--seeds=    other instances in the cluster, comma-separated
--bind=     IP[:port] where to bind the server
"""

# Exit codes
EXIT_OK = 0   # OK
EXIT_HELP = 1 # Help text printed
EXIT_ERR = 2  # Error

# Log entry format
LOG_FORMAT = "%(asctime)s.%(msecs)d %(name)-10s %(levelname)-8s %(message)s"

# Default limits for remove of conf files and for delayed startup
DEF_LOAD_LIMIT = '-7 days'
DEF_RM_LIMIT = '-7 days'

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
		optlist, args = getopt.gnu_getopt( sys.argv[1:], '', 'help version data.d= seeds= bind= load-limit= rm-limit= bootstrap'.split())
	except getopt.GetoptError, err:
		die( 'Parameter error: ' +str( err))
	bind = 'localhost:8001'
	seeds = []
	load_limit = DEF_LOAD_LIMIT
	rm_limit = DEF_RM_LIMIT
	for name, value in optlist:
		if name == "--help":
			print_usage()
		if name == "--version":
			print_usage( True)
		if name == "--data.d":
			config.set_data_dir( value)
		if name == "--bind":
			bind = value
		if name == "--seeds":
			seeds = value.split( ',')
		if name == "--load-limit":
			load_limit = value
		if name == "--bootstrap":
			load_limit = None
		if name == "--rm-limit":
			rm_limit = value

	host, port = helpers.normalize_addr( bind)
	if host is None:
		die( 'Invalid binding address %s'%bind)

	sync.init_cluster_state( '%s:%s'%(host, port))

	# FIXME avoid adding these seeds in cluster
	for seed in seeds:
		r = sync.cluster_state.add_instance( seed)

	# Load old configuration
	config.load_configuration( str_limit=load_limit)
	# Remove old files
	config.set_rm_limit( rm_limit=rm_limit)
	# Run the server
	server.run( ( host, port))

