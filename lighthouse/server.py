#! /usr/bin/python
# Copyright (c) Viliam Holub, Logentries

"""

HTTP server implementation

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
from __init__ import __version__
from __init__ import SERVER_NAME

import data
import sync
import state


RESPONSE_ABOUT = """
Lighthouse

"""

# Responses

RESPONSE_FORBIDDEN = 'Forbidden'
RESPONSE_NOT_LOCKED = 'Not Locked'
RESPONSE_NOT_FOUND = 'Not Found'
RESPONSE_NOT_LOCKED = 'Not Locked'
RESPONSE_NO_CONTENT = 'No Content'
RESPONSE_LOCKED = 'Locked'
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
U_PULL = '/pull'
U_INFO = '/info'
U_PUSH = '/push'
U_STATUS = '/status'


def d( path, beginning):
	return path.startswith( beginning+'/') or path == beginning

def e( path, part):
	return path == part+'/' or path == part


class LighthouseRequestHandler( BaseHTTPServer.BaseHTTPRequestHandler):
	""" Interface to the Loghthouse configuration. """

	def __init__(self, *args):
		self.lock = threading.Lock()
		BaseHTTPServer.BaseHTTPRequestHandler.__init__( self, *args)

	def _parse_params(self):
		try:
			parsed_path = urlparse.urlparse(self.path)
			self.query_params = dict([p.split('=') for p in parsed_path[4].split('&')])
		except:
			self.query_params = {}

	def do_GET(self):
		""" Processes the GET commands. """
		with self.lock:
			path, blocks = self.get_path()
			self._parse_params()
			if path == U_ROOT: self.response_plain( RESPONSE_ABOUT)
			elif d( path, U_DATA): self.get_data( blocks[1:])
			elif d( path, U_UPDATE): self.get_update( blocks[1:])
			elif e( path, U_LOCK): self.get_lock()
			elif d( path, U_PULL): self.get_pull()
			elif e( path, U_INFO): self.get_info()
			elif e( path, U_STATUS): self.get_status()
			else: self.response_not_found()

	def do_PUT(self):
		""" Updates internal data with JSON provided. """
		with self.lock:
			path, blocks = self.get_path()

			if path == U_ROOT: self.response_forbidden()
			elif d( path, U_DATA): self.put_data( blocks[1:])
			elif d( path, U_UPDATE): self.put_update( blocks[1:])
			elif e( path, U_PUSH): self.put_push()
			elif e( path, U_LOCK): self.put_lock()
			else: self.response_not_found()

	def do_DELETE(self):
		""" Deletes the data given. """
		with self.lock:
			path, blocks = self.get_path()

			if path == U_ROOT: self.response_forbidden()
			elif d( path, U_DATA): self.delete_data( blocks[1:])
			elif d( path, U_UPDATE): self.delete_update( blocks[1:])
			elif e( path, U_LOCK): self.delete_lock()
			else: self.response_not_found()
	
	def do_CONNECT(self):
		# TODO
		return self.response_not_found()

	#
	# Lock resource /lock/
	#

	def get_lock(self):
		# Lock info
		name = data.get_lock_code()
		if name != None:
			self.response_plain( name)
		else:
			self.response_not_found( RESPONSE_NOT_LOCKED)

	def put_lock(self):
		""" Put lock """
		code = self.read_input()
		if not code:
			# Invalid lock code, delete the lock
			if data.release_lock():
				data.save_data()
				self.response_plain( RESPONSE_RELEASED)
			else:
				self.response_not_found()
		else:
			# Lock the resource
			# Acquiring the same lock again is idempotent
			if data.try_acquire_lock(code):
				self.response_plain( RESPONSE_ACQUIRED)
			else:
				self.response_forbidden( RESPONSE_LOCKED)

	def delete_lock(self):
		# Abort the update
		if data.abort_update():
			self.response_plain( RESPONSE_RELEASED)
		else:
			self.response_not_found( RESPONSE_NOT_LOCKED)

	#
	# Data /data/
	#

	def _check_version(self):
		query_version, query_checksum = self.query_params.get('version'), self.query_params.get('checksum')
		if query_version or query_checksum:
			version, checksum = data.get_version() # FIXME
			try:
				query_version = int(query_version)
			except ValueError:
				query_version = None
			if (version, checksum) != (query_version, query_checksum):
				return False
		return True

	def get_data(self, blocks):
		""" Data - return data """
		if not self._check_version():
			return self.response_not_found()
		subdata = data.get_data( blocks)
		if subdata:
			self.response_json( subdata)
		else:
			self.response_not_found()

	def put_data(self, blocks):
		subdata = data.get_data( blocks)
		if subdata:
			self.response_forbidden()
		else:
			self.response_not_found()

	def delete_data(self, blocks):
		# Check that the resource exists
		subdata = data.get_data( blocks)
		if not subdata:
			self.response_not_found()
		else:
			self.response_forbidden()

	#
	# Updates /update/
	#

	def check_update(self, blocks):
		""" Checks that update is allowed - the lock is acquired and
		specified in URL. """
		# Ignore update if the lock is not acquired
		if len(blocks) == 0:
			return self.response_not_found()
		# Update does not exist if there is no lock
		lock_code = data.get_lock_code()
		if lock_code is None:
			return self.response_forbidden( RESPONSE_NOT_LOCKED)
		# Check that the lock is correct
		if blocks[0] != lock_code:
			return self.response_forbidden( RESPONSE_INV_LOCK_CODE)
		return False

	def get_update(self, blocks):
		""" Update - return updated data """

		if self.check_update( blocks):
			return

		# Retrieve the data
		subdata = data.get_update( blocks[1:])
		if subdata:
			self.response_json( subdata)
		else:
			self.response_not_found()

	def put_update(self, blocks):
		""" Puts new data """

		if self.check_update( blocks):
			return

		# Get content
		content = self.read_input_json()
		if content is None:
			return self.response_bad_request()
		# Update with the content given
		created = data.update_entry_root( blocks[1:], content)
		if created:
			self.response_created()
		else:
			self.response_not_found()

	def put_push(self):
		""" Pushes new data """

		# Get content
		content = self.read_input_json()
		try:
			far_data = content['data']
			far_server_state = state.ServerState(version=content['version'], checksum=content['checksum'])
		except (TypeError, KeyError):
			return self.response_bad_request()

		# Update with the content given
		if data.push_data(other_data=far_data, other_server_state=far_server_state):
			data.save_data()
		self.response_created()

	def delete_update(self, blocks):
		""" Deletes the given data. Lock must be acquired. """

		if self.check_update( blocks):
			return

		# Retrieve content to update with
		self.read_input()
		# Do the update
		created = data.delete_update( blocks[1:])
		if created:
			self.response_no_content()
		else:
			self.response_not_found()




	def response(self, status, content_type, text, headers=[]):
		self.send_response( status)
		self.send_header( 'Content-type', content_type)
		self.send_header( 'Content-Length', '%s'%len( text))
		for header in headers:
			self.send_header( header[0], header[1])
		self.end_headers()
		self.wfile.write( text)
		return status

	def response_forbidden( self, response = RESPONSE_FORBIDDEN):
		return self.response( 403, 'text/plain', response)

	def response_plain( self, response):
		return self.response( 200, 'text/plain', response)

	def response_json( self, response):
#		return self.response( 200, 'application/json', json.dumps( response))
		return self.response( 200, 'application/json', response)

	def response_created( self, response = RESPONSE_CREATED):
		return self.response( 201, 'application/json', response)

	def response_no_content( self, response = RESPONSE_NO_CONTENT):
		return self.response( 204, 'application/json', response)

	def response_bad_request( self, response = RESPONSE_BAD_REQUEST):
		return self.response( 400, 'text_plain', response)

	def response_not_found( self, response = RESPONSE_NOT_FOUND):
		return self.response( 404, 'text_plain', response)

	def get_path(self):
		url = urlparse.urlparse( self.path)
		components = url.path.split('?',1)[0].split( '/')[1:]
		if len( components) > 0 and components[-1] == '':
			components = components[:-1]
		return url.path, components

	def read_input(self):
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

	def read_input_post(self):
		sent = self.read_input()
		if sent is None:
			return None
		try:
			post = urlparse.parse_qs( sent, keep_blank_values=True,
						strict_parsing=True)
			self.log_message( 'POST: %s', post)
			return post
		except ValueError:
			return None


	def read_input_json(self):
		try:
			sent = self.read_input()
			if sent is not None:
				content = json.loads( sent)
		except ValueError:
			self.log_message( 'JSON: /invalid')
			return None
			
		self.log_message( 'JSON: %s', content)
		return content

	#
	# Pull /pull/
	#

	def get_pull(self):
		""" Pull - return data with server information and data """
		return self.response_json( data.get_pull())

	#
	# Info /info/
	#

	def get_info(self):
		""" Info - return data with server information without data"""
		return self.response_json( data.get_pull(get_data=False))



	#
	# Status /status/
	#

	def get_status(self):
		""" Info - return data with server information without data"""
		return self.response_json( sync.get_servers_status())




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

