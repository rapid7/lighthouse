

# System imports
import _json as json
import urllib2
import logging
import datetime
import sys
import traceback

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
	url = _url( address, '/push')
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
	except:
		_logger.warning( 'Cannot GET data to %s: %s', url, sys.exc_info()[0])
		_logger.warning( '%s', ''.join( traceback.format_tb( sys.exc_info()[2])))
		return None


def info( address):
	str_info = get( address, "/info")
	if str_info is None:
		return None
	return json.loads( str_info)

def pull( address):
	s = get( address, "/pull")
	if s is None:
		return None
	return json.loads( s)


def normalize_addr( addr):
	"""Converts the address to the IP:port format.

	Args:
		addr: address to convert
	Returns:
		Converted address or None if invalid.
	"""
	return addr # FIXME: Better checking :-)

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

