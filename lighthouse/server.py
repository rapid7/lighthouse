#! /usr/bin/python
# Copyright (c) 2012, 2013 Viliam Holub, Logentries

"""HTTP server implementation.

We communicate with the world via HTTP. This is a lightweight HTTP server.

"""

# System imports
from __future__ import with_statement
import BaseHTTPServer
import SocketServer
import _json as json
import sys
import threading
import time
import urlparse

# Local imports
from __init__ import SERVER_NAME
from __init__ import __version__
import data
import sync
import helpers


RESPONSE_ABOUT = """
Lighthouse %s

"""%(__version__)

# Responses

RESPONSE_FORBIDDEN = 'Forbidden'
RESPONSE_NOT_LOCKED = 'Not Locked'
RESPONSE_NOT_FOUND = 'Not Found'
RESPONSE_NOT_LOCKED = 'Not Locked'
RESPONSE_NO_CONTENT = 'No Content'
RESPONSE_LOCKED = 'Locked'
RESPONSE_CONFLICT = 'Conflicting Request'
RESPONSE_CONCURRENT = 'Concurrent Update'
RESPONSE_ACQUIRED = 'Acquired'
RESPONSE_RELEASED = 'Released'
RESPONSE_BAD_REQUEST = 'Bad Request'
RESPONSE_INV_LOCK_CODE = 'Invalid Lock Code'
RESPONSE_CREATED = 'Created'

# URLs

U_ROOT = '/'
U_DATA = '/data'
U_UPDATE = '/update'
U_LOCK = '/lock'
U_VERSION = '/version'
U_COPY = '/copy'
U_VERSION = '/version'
U_STATE = '/state'


def d( path, beginning):
	return path.startswith( beginning+'/') or path == beginning

def e( path, part):
	return path == part+'/' or path == part


class LighthouseRequestHandler( BaseHTTPServer.BaseHTTPRequestHandler):
	""" Interface to the Loghthouse configuration. """

	def __init__(self, *args):
		BaseHTTPServer.BaseHTTPRequestHandler.__init__( self, *args)

	def _parse_params(self):
		try:
			parsed_path = urlparse.urlparse( self.path)
			self.query_params = dict([p.split('=') for p in parsed_path[4].split('&')])
		except:
			self.query_params = {}

	def do_GET(self):
		""" Processes the GET commands. """
		path, blocks = self._get_path()
		self._parse_params()
		if path == U_ROOT: self._response_plain( RESPONSE_ABOUT)
		elif d( path, U_DATA): self.get_data( blocks[1:])
		elif d( path, U_UPDATE): self.get_update( blocks[1:])
		elif e( path, U_LOCK): self.get_lock()
		elif d( path, U_COPY): self.get_copy()
		elif e( path, U_VERSION): self.get_version()
		elif e( path, U_STATE): self.get_state()
		else: self._response_not_found()

	def do_PUT(self):
		""" Updates internal data with JSON provided. """
		path, blocks = self._get_path()

		if path == U_ROOT: self._response_forbidden()
		elif d( path, U_DATA): self.put_data( blocks[1:])
		elif d( path, U_UPDATE): self.put_update( blocks[1:])
		elif e( path, U_COPY): self.put_copy()
		elif e( path, U_LOCK): self.put_lock()
		else: self._response_not_found()

	def do_DELETE(self):
		""" Deletes the data given. """
		path, blocks = self._get_path()

		if path == U_ROOT: self._response_forbidden()
		elif d( path, U_DATA): self.delete_data( blocks[1:])
		elif d( path, U_UPDATE): self.delete_update( blocks[1:])
		elif e( path, U_LOCK): self.delete_lock()
		else: self._response_not_found()
	
	def do_CONNECT(self):
		# TODO
		return self._response_not_found()

	#
	# Lock resource /lock/
	#

	def get_lock(self):
		# Lock info
		name = data.get_lock_code()
		if name != None:
			self._response_plain( name)
		else:
			self._response_not_found( RESPONSE_NOT_LOCKED)

	def put_lock(self):
		""" Put lock """
		code = self._read_input()
		if not code:
			# Missing lock code, delete the lock
			l = data.release_lock()
			if l == data.LCK_OK:
				data.save_data()
				self._response_plain( RESPONSE_RELEASED)
			elif l == data.LCK_CONCURRENT:
				self._response_conflict( RESPONSE_CONCURRENT)
			else:
				self._response_not_found()
		else:
			# Lock the resource
			# Acquiring the same lock again is idempotent
			if data.try_acquire_lock( code):
				self._response_plain( RESPONSE_ACQUIRED)
			else:
				self._response_forbidden( RESPONSE_LOCKED)

	def delete_lock(self):
		# Abort the update
		if data.abort_update():
			self._response_plain( RESPONSE_RELEASED)
		else:
			self._response_not_found( RESPONSE_NOT_LOCKED)

	#
	# Data /data/
	#

	def _check_version(self):
		query_sequence, query_checksum = self.query_params.get('sequence'), self.query_params.get('checksum')
		if query_sequence or query_checksum:
			sequence, checksum = data.get_version() # FIXME
			try:
				query_sequence = int(query_sequence)
			except ValueError:
				query_sequence = None
			if (sequence, checksum) != (query_sequence, query_checksum):
				return False
		return True

	def get_data(self, blocks):
		""" Data - return data """
		if not self._check_version():
			return self._response_not_found()
		subdata = data.get_data( blocks)
		if subdata:
			self._response_json( subdata)
		else:
			self._response_not_found()

	def put_data(self, blocks):
		subdata = data.get_data( blocks)
		if subdata:
			self._response_forbidden()
		else:
			self._response_not_found()

	def delete_data(self, blocks):
		# Check that the resource exists
		subdata = data.get_data( blocks)
		if not subdata:
			self._response_not_found()
		else:
			self._response_forbidden()

	#
	# Updates /update/
	#

	def check_update(self, blocks):
		""" Checks that update is allowed - the lock is acquired and
		specified in URL. """
		# Ignore update if the lock is not acquired
		if len(blocks) == 0:
			return self._response_not_found()
		# Update does not exist if there is no lock
		lock_code = data.get_lock_code()
		if lock_code is None:
			return self._response_forbidden( RESPONSE_NOT_LOCKED)
		# Check that the lock is correct
		if blocks[0] != lock_code:
			return self._response_forbidden( RESPONSE_INV_LOCK_CODE)
		return False

	def get_update(self, blocks):
		""" Update - return updated data """

		if self.check_update( blocks):
			return

		# Retrieve the data
		subdata = data.get_update( blocks[1:])
		if subdata:
			self._response_json( subdata)
		else:
			self._response_not_found()

	def put_update(self, blocks):
		""" Puts new data """

		if self.check_update( blocks):
			return

		# Get content
		content = self._read_input_json()
		if content is None:
			return self._response_bad_request()
		# Update with the content given
		created = data.update_entry_root( blocks[1:], content)
		if created:
			self._response_created()
		else:
			self._response_not_found()

	def delete_update(self, blocks):
		""" Deletes the given data. Lock must be acquired. """

		if self.check_update( blocks):
			return

		# Retrieve content to update with
		self._read_input()
		# Do the update
		created = data.delete_update( blocks[1:])
		if created:
			self._response_no_content()
		else:
			self._response_not_found()
	


	#
	# Copy /copy/
	#

	def get_copy(self):
		""" Returns raw data copy. """
		return self._response_json( data.get_copy())


	def put_copy(self):
		""" Pushes new data """

		# Get content
		content = self._read_input_json()
		try:
			far_data = content['data']
			far_server_state = data.DataVersion(sequence=content['sequence'], checksum=content['checksum'])
		except (TypeError, KeyError):
			return self._response_bad_request()

		# Update with the content given
		if data.push_data( far_data, far_server_state):
			data.save_data()
		self._response_created()


	#
	# Version /version/
	#

	def get_version(self):
		""" Returns data with server information without data. """
		return self._response_json( data.get_copy( get_data=False))


	#
	# State /state/
	#

	def get_state(self):
		""" Returns cluster's state. """
		return self._response_json( sync.cluster_state.get_state())



	#
	# Helpers
	#

	def _response(self, status, content_type, text, headers=[]):
		self.send_response( status)
		self.send_header( 'Content-type', content_type)
		self.send_header( 'Content-Length', '%s'%len( text))
		for header in headers:
			self.send_header( header[0], header[1])
		self.end_headers()
		self.wfile.write( text)
		return status

	def _response_forbidden( self, response = RESPONSE_FORBIDDEN):
		return self._response( 403, 'text/plain', response)

	def _response_conflict( self, response = RESPONSE_CONFLICT):
		return self._response( 409, 'text/plain', response)

	def _response_plain( self, response):
		return self._response( 200, 'text/plain', response)

	def _response_json( self, response):
		return self._response( 200, 'application/json',
				helpers.dump_json( response))

	def _response_created( self, response = RESPONSE_CREATED):
		return self._response( 201, 'application/json', response)

	def _response_no_content( self, response = RESPONSE_NO_CONTENT):
		return self._response( 204, 'application/json', response)

	def _response_bad_request( self, response = RESPONSE_BAD_REQUEST):
		return self._response( 400, 'text_plain', response)

	def _response_not_found( self, response = RESPONSE_NOT_FOUND):
		return self._response( 404, 'text_plain', response)

	def _get_path(self):
		url = urlparse.urlparse( self.path)
		components = url.path.split('?',1)[0].split( '/')[1:]
		if len( components) > 0 and components[-1] == '':
			components = components[:-1]
		return url.path, components

	def _read_input(self):
		try:
			size_raw = self.headers.getheader('Content-Length')
			if size_raw == None:
				return ''
			size = int( size_raw)
			if size < 1:
				return ''
			read = self.rfile.read( size)
		except IOError:
			return None
		return read

	def _read_input_post(self):
		sent = self._read_input()
		if sent is None:
			return None
		try:
			post = urlparse.parse_qs( sent, keep_blank_values=True,
						strict_parsing=True)
			self.log_message( 'POST: %s', post)
			return post
		except ValueError:
			return None


	def _read_input_json(self):
		try:
			sent = self._read_input()
			if sent is not None:
				content = json.loads( sent)
		except ValueError:
			self.log_message( 'JSON: /invalid')
			return None
			
		self.log_message( 'JSON: %s', content)
		return content




class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
	""" Handles requests in separate threads to avoid blocks. """


def run( port=8001):
	LighthouseRequestHandler.server_version = SERVER_NAME +'/' +__version__
	bind_address = ( '', port)
	httpd = ThreadedHTTPServer( bind_address, LighthouseRequestHandler)
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		print 'User break'

