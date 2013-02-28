#!/usr/bin/python

"""Data store representation.

We keep two instances of data. One represents currect state and is immutable.
The other one represents the next state of the data store, being modified by a
client holding a lock.

This data store is protected by a lock to avoid race conditions.

Data can be immediately update asynchronously via push operation.

"""

# System imports
from __future__ import with_statement
import copy
import datetime
import glob
import logging
import md5
import os
import threading
import time

# Local imports
import helpers

# Lock error messages
LCK_OK = 0 # All OK
LCK_NONE = 1 # No lock or lock expired
LCK_CONCURRENT = 2 # Concurrent modification


# Lock timeout in milliseconds
LOCK_TIMEOUT = 30000
# Glob format of a data file
DATA_DIR_GLOB = '????????T??????.??????.json'
DATA_DIR_STRFTIME = '%Y%m%dT%H%M%S.%f.json'

# Logging
_logger = logging.getLogger(__name__)

# Client's lock name, None if the lock is not acquired
_lock_code = None
# Timestamp of client's lock acquire
_lock_timestamp = 0

# Path where we store configuration snapshots. None if undefined.
_data_dir = None


# Threading lock object(s)
# FIXME: Locking can be more optimised, eg. different locks for 
#        different kinds of data.
#        Some data mnipulations can be made out of the critical
#        sections.
_lock = threading.RLock() # reentrant lock, read/write lock would be more handy,
                          # but python std lib doesn't support such locks





def _create_data_dir( data_dir):
	"""Creates the directory safely.
	"""
	try:
		os.makedirs( data_dir)
	except OSError as e:
		if e.errno == 17: # File already exists
			return True
		_logger.warn( 'Cannot create directory: %s: %s', data_dir, e)
		return False
	return True


def set_data_dir(data_dir):
	"""Sets and creates the data directory before start.
	"""
	global _data_dir
	_data_dir = data_dir

	if data_dir is None:
		return None

	if not _create_data_dir( data_dir):
		_data_dir = None
		return False

	return True


class DataVersion:
	"""
	The state we keep for each server. It consists of a number and a
	checksum of the data store.
	"""
	def __init__(self, sequence=0, checksum=''):
		self.sequence = int(sequence)
		self.checksum = checksum

	def __cmp__(self, other):
		""" Compares versions on sequence first, then checksum. """
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
		return DataVersion( sequence=self.sequence, checksum=self.checksum)


class Data:
	"""Data store.

	Data store consists of data itselfs and its version.
	"""

	def __init__( self, copy_data=None, sequence=None):
		"""Initializes the data store.

		If no instance is passed, then the datastore is created empty.

		Args:
			copy_data: Other instance whose data should be copied
				into this new instance or None
			sequence: New sequence to assign or None
		"""
		if copy_data:
			self.data = copy.deepcopy( copy_data.data)
			if sequence:
				self.version = DataVersion( sequence, self.get_checksum())
		else:
			self.data = {}
			self.version = DataVersion( 0, self.get_checksum())

	def load( self, str_data):
		try:
			self.data = helpers.load_json( str_data)
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

	def get( self, path):
		""" Retrieves data subsection.

		Path is an array of element names from the root down to the desired
		field.

		Returns None if the path is invalid.
		"""
		node = self.traverse( self.data, path)
		return node

	def get_checksum( self):
		"""
		Calculates a checksum of the data in a predictable way.
		"""
		m = md5.new()
		m.update( helpers.dump_json( self.data))
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




#
# Data retrieval functions
#

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
	"""Returns lock code or None if there is no lock

	The lock is checked for expiration.

	Returns:
		Log code if successful, None otherwise
	"""
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
	"""Tries to acquire a new lock with the code given.

	Args:
		code: lock code
	Returns:
		True if siccessful
	"""
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



def release_lock():
	"""Releases the client's lock.

	New data are commited.
	"""
	global _data
	global _update
	global _server_state, _uploaded_state
	global _lock_timestamp
	global _lock

	with _lock:
		if get_lock_code() is None:
			return LCK_NONE

		# Check that we can update data, otherwise return concurrent error
		if not _data.version == _update.version:
			return LCK_CONCURRENT

		# Do the update of internal structure
		_data = Data( _update, _update.version.sequence+1)
		_update = Data()
		_lock_timestamp = 0
		return LCK_OK


def abort_update():
	"""Terminates the current update.
	"""
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
def push_data( other_data, other_version):
	global _data
	global _server_state
	global _lock
	with _lock:
		if other_version <= _server_state:
			return False
		new_data = Data()
		new_data.data = other_data # Note: other_data must not be used or modified later
		_data = new_data
		_server_state = other_version
		return True


def _load_from_file():
	global _data_dir

	# Do not read file if there is no data path defined
	if _data_dir is None:
		return None

	dir_glob = _data_dir +'/' +DATA_DIR_GLOB
	_logger.debug( 'Data dir glob: %s', dir_glob)

	files = glob.glob( dir_glob)
	for name in sorted( files, reverse=True):
		try:
			with open( name, 'r') as f:
				content = helpers.load_json( f.read())
				#d = Data.from_copy( content)
				#if d:
				if content['version'] and content['data']:
					_logger.info( 'Loading state from %s', name)
					return content
		except (IOError, ValueError, KeyError) as e:
			_logger.warn( 'Cannot read file %s with json configuration %s', name, e)
	_logger.warn('No configuration found')
	return None


def _save_to_file():
	global _data_dir
	global _lock

	# Don't write if there's no destination
	if _data_dir is None:
		return False

	# Get a raw copy of all data
	data_copy = get_copy()

	# Write this configuration
	file_name = _data_dir + '/' + datetime.datetime.now().strftime( DATA_DIR_STRFTIME)
	with open(file_name, 'w') as f:
		f.write( helpers.dump_json( data_copy))
	return True


def load_data():
	content = _load_from_file()
	if content:
		return push_data( DataVersion( sequence=content[ 'sequence'], checksum=content[ 'checksum']), content[ 'data'])
	return False


def save_data():
	return _save_to_file()


def get_copy( get_data=True):
	"""Returns raw copy of current data, including version information.

	Args:
		get_data: include complete copy of data store
	"""
	global _data, _server_state
	global _lock

	with _lock:
		response = {}
		# Collect data version
		response[ 'version'] = _data.version.to_dict()
		# Collect data if required
		if get_data:
			response[ 'data'] = _data.data
		# Return response
		return response


def cur_data():
	"""Returns the current data store. It is immutable thus safe for other
	threads to access it.
	"""
	global _data
	return _data

