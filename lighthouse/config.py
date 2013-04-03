
"""Manipulates with the whole configuration.

Configuration consists of the whole data store copy and cluster state.

"""

# System imports
import os
import glob
import logging
import datetime

# Local imports
import sync
import helpers
import data

_logger = logging.getLogger(__name__)

# Glob format of a data file
DATA_DIR_GLOB = '????????T??????.??????.json'
DATA_DIR_STRFTIME = '%Y%m%dT%H%M%S.%f.json'

# Path where we store configuration snapshots. None if undefined.
_data_dir = None

# string describing datetime limit for removing of old configuration files
#  any format that can be [arsed by load_time
_rm_limit = None

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


def set_rm_limit(rm_limit):
	"""
	"""
	global _rm_limit
	_rm_limit = rm_limit


def save_configuration():
	global _data_dir

	# Don't write if there's no destination
	if _data_dir is None:
		return False

	snapshot = {}
	# Get a raw copy of all data
	snapshot[ 'copy'] = data.get_copy()
	# Get current system state
	snapshot[ 'cluster'] = sync.cluster_state.get_state()

	# Write this configuration
	file_name = _data_dir + '/' +helpers.now().strftime( DATA_DIR_STRFTIME)
	with open(file_name, 'w') as f:
		f.write( helpers.dump_json( snapshot))
	return True


def _load_from_content( content):
	# Content must contain data and state
	if not 'copy' in content or not 'cluster' in content:
		return False

	if data.push_data( content[ 'copy']):
		sync.cluster_state.update_state( content[ 'cluster'])
		return True
	return False


def _load_from_file( filename):
	try:
		with open( filename, 'r') as f:
			content = helpers.load_json( f.read())
	except (IOError, ValueError, KeyError) as e:
		_logger.warn( 'Cannot read file %s with json configuration %s', filename, e)
		return False

	r = _load_from_content( content)
	if r:
		_logger.info( 'Loading %s', filename)
	return r


def _is_newer_path( limit, file_path):
	if limit is None:
		return True
	t = datetime.datetime.strptime(os.path.basename(file_path), DATA_DIR_STRFTIME)
	return limit < t


def rm_old_files ( str_limit=None):
	global _data_dir

	limit = helpers.load_time( str_limit)
	if limit is None:
		return None

	dir_glob = _data_dir +'/' +DATA_DIR_GLOB
	files = glob.glob( dir_glob)
	for filename in sorted( files, reverse=True):
		if not _is_newer_path( limit, filename):
			_logger.info( 'Removing config file: [%s]', filename)
#			os.unlink( filename)


def load_configuration( str_limit=None):
	"""Loads data from the newest file.

	Returns:
		Latest data or empty data if no suitable file was found.
	"""
	global _data_dir

	rm_old_files()

	limit = helpers.load_time( str_limit)
	# Do not read file if there is no data path defined
	if _data_dir is None:
		_logger.info( 'No data.d defined, starting plain')
		return None

	dir_glob = _data_dir +'/' + DATA_DIR_GLOB
	_logger.debug( 'Data dir glob: %s', dir_glob)

	files = glob.glob( dir_glob)
	for filename in sorted( files, reverse=True):
		if not _is_newer_path( limit, filename):
			_logger.warn( 'Configuration too old, switching to Service Unavailable state')
			data.set_unavailable()
			return True
		if _load_from_file( filename):
			return True

	_logger.warn( 'No configuration found')
	return False

