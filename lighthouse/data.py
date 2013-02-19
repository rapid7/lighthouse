#!/usr/bin/python

from __future__ import with_statement

import _json as json
import copy
import glob
import time
import md5
import random
import threading
import datetime
import logging

import state


# Lock timeout in milliseconds
LOCK_TIMEOUT = 30000
# Glob format of a data file
DATA_DIR_GLOB = '????-??-??T??:??:??.??????.json'
DATA_DIR_STRFTIME = '%Y-%m%dT%H:%M:%S.%f.json'

# Logging
logger = logging.getLogger(__name__)

# Lock name, None is the lock is not acquired
_lock_timestamp = 0
_lock_code = None

# Threading lock object(s)
# FIXME: Locking can be more optimised, eg. different locks for 
#        different kinds of data.
#        Some data mnipulations can be made out of the critical
#        sections.
_lock = threading.RLock() # reentrant lock, read/write lock would be more handy,
                          # but python std lib doesn't support such locks



def load_json(s):
	return json.loads( s)

def dump_json(jsn):
	return json.dumps( jsn, sort_keys=True, indent=2, check_circular=False)


_data_dir = None
def set_data_dir(data_dir):
	global _data_dir
	_data_dir = data_dir


class Data:
	def __init__( self, init_data = None):
		if init_data:
			self.data = copy.deepcopy( init_data.data)
		else:
			self.data = {}

	def load( self, str_data):
		try:
			self.data = load_json( str_data)
		except ValueError:
			return False
		return True

	@staticmethod
	def traverse( what, path):
		""" Traverses the data tree following the path given.

		Return data subsection or None.
		"""
		# Begin in root
		node = what
		# Continue in the path
		for elem in path:
			try:
				if isinstance( node, list):
					# If it is a list, try to index it
					node = node[ int(elem)]
				elif isinstance( node, dict):
					# If it is a dict, retrieve by a name
					node = node[ elem]
				else:
					# This is a leaf and cannot be sub-indexed
					return None
			except (ValueError, KeyError, IndexError):
				return None
		return node

	@staticmethod
	def dump_json(node):
		if node != None:
			return dump_json( node)
		else:
			return None


	def get( self, path):
		""" Retrieves data subsection.

		Path is an array of element names from the root down to the desired
		field.

		Returns None if the path is invalid.
		"""
		node = self.traverse( self.data, path)
		return self.dump_json(node)


	def pull( self):
		return self.traverse( self.data, [])


	def get_checksum( self):
		"""
		"""
		m = md5.new()
		m.update( self.get( []))
		return m.hexdigest()


	def set( self, path, content):
		""" Stores the content given and the position specified.
		
		Path must not point to the root.

		Returns True is the content has been submitted.
		"""
		if len( path) == 0:
			self.data = content
			return True

		last = path[-1]
		node = self.traverse( self.data, path[:-1])
		if not node:
			return False
		# Check where we are
		if isinstance( node, list):
			# Store at index
			# FIXME - index points after end?
			node[ int(last)] = content
			return False #FIXME: here we should return True, shouldn't we?
		elif isinstance( node, dict):
			# If it is a dict, retrieve by a name
			node[ last] = content
		else:
			# This is a leaf and cannot be addressed
			return False

		return True

	def delete( self, path):
		""" Removes the specified data subsection.

		Path must not point to the root.

		Returns True if the section has been found.
		"""
		if len( path) == 0:
			self.data = {}
			return True
		
		last = path[-1]
		node = self.traverse( self.data, path[:-1])
		if not node:
			return None

		# Perform the detele operation
		try:
			if isinstance( node, list):
				# Delete item by index
				del node[ int(last)]
			elif isinstance( node, dict):
				# If it is a dict, retrieve by a name
				del node[ last]
			else:
				# This is a leaf and cannot be sub-indexed
				return False
		except (ValueError, KeyError, IndexError):
			return False

		return True


# Data structure
_data = Data()
# Update structure
_update = Data()

_server_state = state.ServerState(version=0, checksum=_data.get_checksum())
_uploaded_state = None


def get_data( path):
	global _data, _lock
	with _lock:
		return _data.get( path)

def get_update( path):
	global _update, _lock
	with _lock:
		return _update.get( path)

def update_entry_root( path, content):
	global _update, _lock
	with _lock:
		return _update.set( path, content)

def delete_data( path):
	global _data, _lock
	with _lock:
		return _data.delete( path)

def delete_update( path):
	global _update, _lock
	with _lock:
		return _update.delete( path)
#
# Lock management
#

def _timestamp():
	return int( time.time()*1000)


def get_lock_code():
	global _lock_timestamp
	global _lock_code
	global _update
	global _lock
	with _lock:
		if _lock_timestamp == 0:
			# Unlocked
			return None
		else:
			# Locked unless the lock expired
			now = _timestamp()
			if now-_lock_timestamp > LOCK_TIMEOUT:
				_lock_timestamp = 0
				_lock_code = ''
				_update = Data()
				return None
			return _lock_code

def try_acquire_lock( code):
	global _data
	global _update
	global _lock_code
	global _lock_timestamp
	global _lock

	with _lock:
		# Get current lock
		current_lock = get_lock_code()
		# If the lock is already acquired and it's not the same, fail
		if current_lock is not None and current_lock != code:
			return False

		# Set new lock timestamp
		_lock_timestamp = _timestamp()
		# If it is a new lock, copy its name and data to update
		if current_lock != code:
			_lock_code = code
			_update = Data( _data)
		return True


def _inc_server_state():
	global _server_state

	version = _server_state.version + 1
	checksum = _data.get_checksum()
	_server_state = state.ServerState(version=version, checksum=checksum)


def release_lock():
	global _data
	global _update
	global _server_state, _uploaded_state
	global _lock_timestamp
	global _lock

	with _lock:
		if get_lock_code() is None:
			return False

		# TODO
		# Do the update of internal structure
		_data  = _update
		_inc_server_state()
		_uploaded_state = _server_state
		_update = Data()
		_lock_timestamp = 0
		return True


def abort_update():
	global _data
	global _update
	global _lock_timestamp
	global _lock

	with _lock:
		if get_lock_code() is None:
			return False
		_update = Data()
		_lock_timestamp = 0
		return True


#FIXME: data is both content of the request as a dict or instance of Data here
def push_data( other_data, other_server_state):
	global _data
	global _server_state
	global _lock
	with _lock:
		if other_server_state <= _server_state:
			return False
		new_data = Data()
		new_data.data = other_data # Note: other_data must not be used or modified later
		_data = new_data
		_server_state = other_server_state
		return True


def _load_from_file():
	global _data_dir
	data_dir = _data_dir

	if data_dir == None:
		return None

	files = glob.glob( data_dir +'/' +DATA_DIR_GLOB)
	for name in sorted( files, reverse=True):
		try:
			with open( name, 'r') as f:
				content = load_json( f.read())
				if content['checksum'] and content['version'] and content['data']:
					logger.info('Uploaded configuration: [%s]', name)
					return content
		except (IOError, ValueError, KeyError):
			pass
	logger.warn('No configuration found')
	return False


def _save_to_file():
	global _data_dir
	global _data, _server_state
	global _lock
	data, server_state = None, None
	with _lock:
		data = _data
		server_state = server_state
	if data is None:
		return
	x = {
		'version':server_state.version,
		'checksum':server_state.checksum,
		'data':data,
	}

	file_name = _data_dir + '/' + DATA_DIR_STRFTIME
	with open(file_name, 'w') as f:
		f.write(dump_json(x))


def load_data( data_dir):
	global _data
	global _lock
	# FIXME: Must save and load whole pull, not only data and set version/checksum accordingly
	#        Maybe we can call push_data(...) here.
	content = _load_from_file( data_dir)
	if content:
		return push_data(other_server_state=state.ServerState(version=content['version'], checksum=content['checksum']), other_data=content['data'])
	return False


def get_pull( get_data = True):
	global _data, _server_state
	global _lock

	with _lock:
		pull = {
			'version':_server_state.version,
			'checksum':_server_state.checksum,
		}
		if get_data:
			pull['data'] = _data.pull()
		return dump_json(pull)



def dump_time(time):
	if time is None:
		return None
	return time.strftime("%Y%m%dT%H%M%S")


class PushInfo(object):
	def __init__(self, state=None, uploaded=None, data=None):
		self.state = state
		self.uploaded = uploaded
		self.data = data


def cur_state(push_info):
	global _data, _server_state, _uploaded_state
	global _lock

	data, state, uploaded = (None,)*3
	with _lock:
		data = _data
		state = _server_state
		uploaded = _uploaded_state
	push_info.data = data.data
	push_info.state = state
	push_info.uploaded = uploaded
	return push_info
