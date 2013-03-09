

# System imports
import _json as json
import urllib2
import logging
import datetime, time
import sys
import socket
import traceback

DEFAULT_PORT = 8001

_logger = logging.getLogger(__name__)


NOTIME = datetime.datetime( 1900, 1, 1, 0, 0, 0)


def _url( address, path='/'):
	if len(path) < 1 or path[0] != '/':
		raise TypeError()
	return "http://%s%s" % (address, path)



def push( address, content):
	"""Pushes the content given via HTTP PUT to update the remote
	instance.

	It does not fail on any errors.

	Args:
		address: destination
		content: distionary to send as JSON
	Retruns:
		True if successful
	"""
	url = _url( address, '/copy')
	opener = urllib2.build_opener( urllib2.HTTPHandler)
	request = urllib2.Request( url, data=content)
	request.add_header( 'Content-Type', 'application/json')
	request.get_method = lambda: 'PUT'
	try:
		url = opener.open( request)
	except:
		_logger.warning( 'Cannot PUT data to %s: %s', url, sys.exc_info()[0])
		_logger.warning( '%s', ''.join( traceback.format_tb( sys.exc_info()[2])))
		return False
		
	return True


def get( address, path):
	url = _url( address, path)
	try:
		f = urllib2.urlopen( url)
		s = f.read()
		return s
	except urllib2.URLError:
		_logger.debug( '    %s: %s', url, sys.exc_info()[1])
		return None
	except:
		_logger.warning( 'Cannot GET data from %s: %s %s', url, sys.exc_info()[0], sys.exc_info()[1])
		_logger.warning( '%s', ''.join( traceback.format_tb( sys.exc_info()[2])))
		return None


def info( address):
	str_info = get( address, "/state")
	if str_info is None:
		return None
	return json.loads( str_info)

def pull( address):
	s = get( address, "/copy")
	if s is None:
		return None
	return json.loads( s)


def normalize_addr( addr):
	"""Converts and checks that the address is in host:port format.

	Args:
		addr: address to convert
	Returns:
		Converted typle containing IP address and port number.
		None otherwise.
	"""
	# Split addresss into components
	pair = addr.split( ':')
	if len(pair) > 2:
		return None, None

	# Convert host part
	host = socket.gethostbyname( pair[0])

	# Convert port part
	if len(pair) < 2:
		port = DEFAULT_PORT
	else:
		port = None
		try:
			port = int( pair[1])
		except ValueError:
			pass
		if port is None or port < 1 or port > 65535:
			return (None, None)

	return (host, port)

def now():
	"""Returns current time."""
	return datetime.datetime.now()


def load_json( s):
	return json.loads( s)

def dump_json( data):
	""" Converts the configuration into human-readable string.
	
	This conversion must be predictable. This means that the same
	configuration will always be converted into the same string.

	Args:
		data: Data for conversion
	"""
	if data == None:
		return None
	return json.dumps( data, sort_keys=True, indent=2, check_circular=False)


def dump_time( time):
	if time is None:
		return None
	return time.strftime( "%Y%m%dT%H%M%S")


def load_time( s):
	if s is None:
		return None
	return time.strptime( s, "%Y%m%dT%H%M%S")
