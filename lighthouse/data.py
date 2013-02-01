#!/usr/bin/python

from __future__ import with_statement

import _json as json
import copy
import glob
import time


# Lock timeout in milliseconds
LOCK_TIMEOUT = 30000
# Glob format of a data file
DATA_DIR_GLOB = '????-??-?? ??:??:??.???'

# Lock name, None is the lock is not acquired
lock_timestamp = 0
lock_code = None


class Data:
	def __init__( self, init_data = None):
		if init_data:
			self.data = copy.deepcopy( init_data.data)
		else:
			self.data = {}

	def load( self, str_data):
		try:
			self.data = json.loads( str_data)
		except ValueError:
			return False
		return True

	def load_from_file( self, data_dir):
		if data_dir == None:
			self.data = {}
			return

		files = glob.glob( data_dir +'/' +DATA_DIR_GLOB)
		for name in sorted( files, reverse=True):
			try:
				with open( name, 'r') as f:
					if self.load( f.read()):
						print 'Uploaded configuration ' +name
						return True
			except IOError:
				pass
		print 'No configuration found'
		return False

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

		Path is an array of element names from the root donw to the desired
		field.

		Returns None if the path is invalid.
		"""
		node = self.traverse( self.data, path)
		if node != None:
			return json.dumps( node, sort_keys=True, indent=2, check_circular=False)
		else:
			return None

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
			return False
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
data = Data()
# Update structure
update = Data()


def get_data( path):
	global data
	return data.get( path)

def get_update( path):
	global update
	return update.get( path)

def update_entry_root( path, content):
	global update
	return update.set( path, content)

def delete_data( path):
	global data
	return data.delete( path)

def delete_update( path):
	global update
	return update.delete( path)
#
# Lock management
#

def timestamp():
	return int( time.time()*1000)


def get_lock_code():
	global lock_timestamp
	global lock_code
	global update
	if lock_timestamp == 0:
		# Unlocked
		return None
	else:
		# Locked unless the lock expired
		now = timestamp()
		if now-lock_timestamp > LOCK_TIMEOUT:
			lock_timestamp = 0
			lock_code = ''
			update = Data()
			return None
		return lock_code

def try_acquire_lock( code):
	global data
	global update
	global lock_code
	global lock_timestamp

	# Get current lock
	current_lock = get_lock_code()
	# If the lock is already acquired and it's not the same, fail
	if current_lock is not None and current_lock != code:
		return False

	# Set new lock timestamp
	lock_timestamp = timestamp()
	# If it is a new lock, copy its name and data to update
	if current_lock != code:
		lock_code = code
		update = Data( data)
	return True

def release_lock():
	global data
	global update
	global lock_timestamp

	if get_lock_code() is None:
		return False

	# TODO
	# Do the update of internal structure
	data = update
	update = Data()
	lock_timestamp = 0
	return True

def abort_update():
	global data
	global update
	global lock_timestamp
	if get_lock_code() is None:
		return False
	update = Data()
	lock_timestamp = 0
	return True


def load_data( data_dir):
	global data
	return data.load_from_file( data_dir)

