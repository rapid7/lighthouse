
"""Simple instance synchronization, aka monitor.

For method synchronization simple decorate the method with @synchronized.
Note that the constructor must be decorated as well to ensure that the
instance lock is created before its methods are called concurrently.

Viliam Holub

"""

# System imports
import threading
import functools


def add_lock( instance):
	"""Adds lock to the instance given.

	Args:
		instance: instance where to add the lock
	"""
	lock = threading.RLock()
	instance._lock = lock
	return lock


def synchronized( method):
	"""A decorator to guard a method with instance lock. """

	@functools.wraps( method)
	def _wrap( self, *args, **kwargs):
		# Get instance lock
		lock = getattr( self, '_lock', None)
		if not lock:
			lock = add_lock( self)

		# Lock the instance
		lock.acquire()
		try:
			return method( self, *args, **kwargs)
		finally:
			# Unlock the instance in all cases
			lock.release()

	return _wrap

