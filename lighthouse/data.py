#!/usr/bin/python

"""Data store representation.

We keep two instances of data. One represents currect state and is immutable.
The other one represents the next state of the data store, being modified by a
clicked holding a lock.

This data store is protected by a lock to avoid race conditions.


"""

# System imports
from __future__ import with_statement
import _json as json
import copy
import datetime
import glob
import logging
import md5
import os
import threading
import time


# Lock timeout in milliseconds
LOCK_TIMEOUT = 30000
# Glob format of a data file
DATA_DIR_GLOB = '????????T??????.??????.json'
DATA_DIR_STRFTIME = '%Y%m%dT%H%M%S.%f.json'

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


_data_dir = None


def load_json(s):
	return json.loads( s)

def dump_json(jsn):
	"""
	Converts the configuration into human-readable string. This conversion
	must be predictable. This means that the same configuration will always
	be converted into the same string.
	"""
	return json.dumps( jsn, sort_keys=True, indent=2, check_circular=False)


def _create_data_dir(data_dir):
	try:
		os.makedirs(data_dir)
	except OSError as e:
		if e.errno == 17: # File already exists
			return True
		logger.warn("Cannot create directory: [%s] : %s", data_dir, e)
		return False
	return True


def set_data_dir(data_dir):
	global _data_dir

	if data_dir is None:
		with _lock:
			_data_dir = None
		return None

	if not _create_data_dir(data_dir):
		with _lock:
			_data_dir = None
		return False

	_data_dir = data_dir

	return True


class DataVersion(object):
	"""
	The state we keep for each server. It consists of a number and a
	checksum of the data store.
	"""
	def __init__(self, sequence = None, checksum=None):
		if sequence is None or checksum is None:
			raise TypeError() # FIXME: Really TypeError ?
		self.sequence = int(sequence)
		self.checksum = checksum

	def __cmp__(self, other):
		"""
		We compare states on sequence first, then checksum.
		"""
		if other is None:
			return +1

		if self.sequence > other.sequence:
			return +1
		elif self.sequence < other.sequence:
			return -1

		if self.checksum > other.checksum:
			return +1
		elif self.checksum < other.checksum:
			return -1
		return 0

	def to_dict(self):
		return {
			'sequence': self.sequence,
			'checksum': self.checksum,
		}

	def clone(self):
		return DataVersion(sequence=self.sequence, checksum=self.checksum)


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
		Calculates a checksum of the data in a predictable way.
		"""
		m = md5.new()
		m.update( self.dump_json( self.data))
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

_server_state = DataVersion(sequence=0, checksum=_data.get_checksum())
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

	sequence = _server_state.sequence + 1
	checksum = _data.get_checksum()
	_server_state = DataVersion(sequence=sequence, checksum=checksum)


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

	if _data_dir is None:
		return None

	dir_glob = _data_dir +'/' +DATA_DIR_GLOB
	logger.debug("data dir glob: %s", dir_glob)
	files = glob.glob( dir_glob)
	for name in sorted( files, reverse=True):
		try:
			with open( name, 'r') as f:
				content = load_json( f.read())
				if content['checksum'] and content['sequence'] and content['data']:
					logger.info('Uploaded configuration: [%s]', name)
					return content
		except (IOError, ValueError, KeyError) as e:
			logger.warn("Cannot read file %s with json configuration: %s", name, e)
	logger.warn('No configuration found')
	return False


def _save_to_file():
	global _data_dir
	global _data, _server_state
	global _lock

	if _data_dir is None:
		return None

	data, server_state = None, None
	with _lock:
		data = _data
		server_state = _server_state
	if data is None:
		return None
	x = {
		'sequence':server_state.sequence,
		'checksum':server_state.checksum,
		'data':data.data,
	}
	file_name = _data_dir + '/' + datetime.datetime.now().strftime(DATA_DIR_STRFTIME)
	with open(file_name, 'w') as f:
		f.write(dump_json(x))
	return True


def load_data():
	content = _load_from_file()
	if content:
		return push_data(other_server_state=DataVersion(sequence=content['sequence'], checksum=content['checksum']), other_data=content['data'])
	return False


def save_data():
	return _save_to_file()


def get_pull( get_data = True):
	global _data, _server_state
	global _lock

	with _lock:
		pull = {
			'sequence':_server_state.sequence,
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


def cur_state():
	"""Returns the current state of all data.

	That contains current data, sequence, checksum, and uploaded state.
	"""
	global _data, _server_state, _uploaded_state
	global _lock

	s = PushInfo()
	with _lock:
		s.data = _data.data
		s.state = _server_state
		s.uploaded = _uploaded_state
	return s

