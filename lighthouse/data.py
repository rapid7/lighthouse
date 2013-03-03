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
import logging
import md5
import threading
import time
import copy

# Local imports
import helpers

# Lock error messages
LCK_OK = 0 # All OK
LCK_NONE = 1 # No lock or lock expired
LCK_CONCURRENT = 2 # Concurrent modification


# Lock timeout in milliseconds
LOCK_TIMEOUT = 30000

# Logging
_logger = logging.getLogger(__name__)

# Client's lock name, None if the lock is not acquired
_lock_code = None
# Timestamp of client's lock acquire
_lock_timestamp = 0


# Threading lock object(s)
# FIXME: Locking can be more optimised, eg. different locks for 
#        different kinds of data.
#        Some data mnipulations can be made out of the critical
#        sections.
_lock = threading.RLock() # reentrant lock, read/write lock would be more handy,
                          # but python std lib doesn't support such locks






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

	@staticmethod
	def from_dict( d):
		return DataVersion( d['sequence'], d['checksum'])

	def clone(self):
		return DataVersion( sequence=self.sequence, checksum=self.checksum)


class Data:
	"""Data store.

	Data store consists of data itselfs and its version.
	"""

	def __init__( self, new_data={}, sequence=0):
		"""Initializes the data store.

		If no instance is passed, then the datastore is created empty.

		Args:
			new_data: Data to be used in this instance, making a copy of it
			sequence: New sequence to assign or None
		"""
		self.data = copy.deepcopy( new_data)
		self.version = DataVersion( sequence, self.get_checksum())

	@staticmethod
	def copy( inst):
		return Data( inst.data, inst.version.sequence)

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
			_update = Data.copy( _data)
		return True



def release_lock():
	"""Releases the client's lock.

	New data are commited.
	"""
	global _data
	global _update
	global _lock_timestamp
	global _lock

	with _lock:
		if get_lock_code() is None:
			return LCK_NONE

		# Check for source version
		ch_old = _data.version == _update.version

		# Increase sequence number for updated data store
		_update.version.sequence += 1
		# Create a copy of updated data store with new version
		new_data = Data.copy( _update)

		# Check for destination version
		ch_new = new_data.version == _update.version

		# Check that we can update data, otherwise return concurrent error
		if not ch_old and not ch_new:
			return LCK_CONCURRENT

		# Do the update of internal structure
		_data = new_data
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


def push_data( copy):
	global _logger, _data, _lock

	try:
		copy_ver = DataVersion.from_dict( copy[ 'version'])
		copy_data = copy[ 'data']
	except KeyError as e:
		_logger.error( 'Invalid or missing version in copy')
		return False


	with _lock:
		# Do not accept configuration if it's older
		if copy_ver <= _data.version:
			return False
		# Configuration is newer, upload it
		_data = Data( copy_data, copy_ver.sequence)
		return True


def get_copy( get_data=True):
	"""Returns raw copy of current data, including version information.

	Args:
		get_data: include complete copy of data store
	"""
	global _data, _lock

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

