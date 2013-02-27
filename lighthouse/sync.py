
# System imports
import copy
import datetime
import logging
import random
import sys
import threading
import time
import traceback
import urllib2

# Local imports
import data

# Period between pings in seconds
PING_PERIOD = 0.2
# Maximal delay for push/pull operation
REACTION_VAR = 0.01

logger = logging.getLogger(__name__)


from functools import wraps

def synchronous( tlockname ):
	"""A decorator to place an instance based lock around a method """

	def _synched(func):
		@wraps(func)
		def _synchronizer(self,*args, **kwargs):
			tlock = self.__getattribute__( tlockname)
			tlock.acquire()
			try:
				return func(self, *args, **kwargs)
			finally:
				tlock.release()
		return _synchronizer
	return _synched


class InstanceState:
	"""Describes state of an instance.
	"""

	def __init__(self, address):
		"""Initializes the state with address given. All other
		attributes are set to default valuse.
		"""
		# Address of the instance as a string of the form ip:port or
		# host:port. It is immutable.
		self.address = address

		# Last state that was pushed to the server (instance of DataVersion or None)
		self.uploaded_state = None
		# Last state of the server received by ping (instance of DataVErsion or None)
		self.ping_state = None
		# If last ping successed
		self.reachable = False
		# Time of the last ping (DateTime)
		self.last_ping = None
		# Time of the last push (DateTime)
		self.last_upload = None

	def to_dict(self):
		return {
			'address': self.address,
			'uploaded-state': self.uploaded_state and self.uploaded_state.to_dict() or None,
			'ping-state': self.ping_state and self.ping_state.to_dict() or None,
			'reachable': self.reachable,
			'last-ping': data.dump_time(self.last_ping),
			'last-upload': data.dump_time(self.last_upload),
		}


class Monitor(threading.Thread):
	"""Monitors the instance given for updates.

	Runs in its own thread. It follows the ping/pull/push pattern.
	"""

	def __init__(self, instance_state):
		"""Initializes the monitor with instance state given.
		"""
		# Initialize the thread as daemon
		super(Monitor, self).__init__(name="Monitor %s"%instance_state.address)
		self.daemon = True

		# Instance state this monitor is responsible for
		self.instance_state = instance_state
		# Asynchronous communicaton - push request
		self.force_push = threading.Event()

	
	def run(self):
		"""Runs the cycle ping/pull/push.
		"""
		while True:
			# Wait for push signal or timeout
			do_push = self.force_push.wait( PING_PERIOD)
			# Wait little bit more to avoid update storms
			time.sleep( random.random( REACTION_VAR))
			if do_push:
				# TODO - push
				pass
			else:
				# TODO - ping
				pass





class ClusterState:
	"""Describes state of the cluster.
	"""


	def __init__(self):
		"""Initializes the cluster state with all entries empty.
		"""
		# Lock to guard this instance
		self.lock = threading.RLock()
		# States of all visible instances
		self.instance_states = []
		# Instance monitors
		self.monitors = []


	def add_instance(self, xaddr):
		"""Adds a new instance to the cluster. New Push and Pull
		monitors are created.

		Args:
			xaddr: address in the form of ip:port or host:port
		Returns:
			True is successful, False otherwise
		"""
		# Normalize and check the address
		addr = _normalize_addr( xaddr)
		if not addr:
			return False

		with self.lock:
			# Check that the address is not in our list already
			if any( [addr == x.address for x in self.instance_states]):
				return True
			# Create a new state for the instance
			instance_state = InstanceState( addr)
			self.instance_states.append( instance_state)
			# Instantiate and start a monitor
			monitor = Monitor( instance_state)
			monitor.start()
			self.monitors.append( monitor)

	def get_state(self):
		"""Returns JSON-encoded state of the cluster.
		"""
		with self.lock:
			return data.dump_json( [x.to_dict()
					for x in self.instance_states])



class Sync:
	"""
	Synchronizes instances in the cluster.
	"""

	def __init__(self):
		self._stop = False
		self.push_info = data.PushInfo()

	@staticmethod
	def _url(address, path='/'):
		if len(path) < 1 or path[0] != '/':
			raise TypeError()
		return "http://%s%s" % (address, path)

	@staticmethod
	def _push(address, content):
		url = Sync._url(address, '/push')
		opener = urllib2.build_opener(urllib2.HTTPHandler)
		request = urllib2.Request(url, data=content)
		request.add_header('Content-Type', 'application/json')
		request.get_method = lambda: 'PUT'
		try:
			url = opener.open(request)
		except urllib2.URLError as e:
			logger.warning("Cannot PUT data to [%s] : %s", url, e)
			return False
		return True

	@staticmethod
	def _get(address, path):
		url = Sync._url(address, path)
		try:
			f = urllib2.urlopen(url)
			s = f.read()
			return s
		except urllib2.URLError as e:
			logger.warning("Cannot GET data from [%s] : %s", url, e)
			return None

	@staticmethod
	def _pull(address):
		s = Sync._get(address, "/pull")
		if s is None:
			return None
		return data.load_json(s)


	@staticmethod
	def _info(address):
		str_info = Sync._get(address, "/info")
		if str_info is None:
			return None
		return data.load_json(str_info)


	def _try_push_one(self):
		"""Tries to push the current data to other instance.
		"""
		global _servers
		if not self.push_info.uploaded or self.push_info.uploaded != self.push_info.state:
			return False
		push_info_state = self.push_info.state
		if any([ x.ping_state and push_info_state < x.ping_state for x in _servers ]):
			return False
		candidates = [ x for x in _servers if x.reachable and (x.uploaded_state is None or x.uploaded_state < push_info_state) and (x.ping_state is None or x.ping_state < push_info_state) ] # Note: at present x.reachable if and only if x.ping_state is not None
		if 0 == len(candidates):
			return False
		server_desc = random.choice(candidates)
		logger.info("Trying to push data to [%s]", server_desc.address)
		server_desc.uploaded_state = push_info_state
		server_desc.last_upload = datetime.datetime.now()
		if not Sync._push(address=server_desc.address, content=data.dump_json({'sequence':self.push_info.state.sequence, 'checksum':self.push_info.state.checksum, 'data':self.push_info.data})):
			server_desc.reachable = False
			return True
		return True

	def _try_ping_one(self):
		global _servers
		now = datetime.datetime.now()
		threshold = now - datetime.timedelta(seconds=60)
		candidates = [ x for x in _servers if x.last_ping is None or x.last_ping <= threshold ]
		if 0 == len(candidates):
			return False
		server_desc = random.choice(candidates)
		logger.info("Trying to ping [%s]", server_desc.address)
		info = Sync._info(address=server_desc.address)
		server_desc.last_ping = now
		if not info:
			server_desc.reachable = False
			return True
		server_desc.ping_state = data.DataVersion(sequence=info['sequence'], checksum=info['checksum'])
		server_desc.reachable = True
		return True

	def _try_pull_one(self):
		global _servers
		try:
			max_state = max([ x.ping_state for x in _servers if x.ping_state is not None ])
		except ValueError:
			max_state = None
		if max_state is None or max_state <= self.push_info.state:
			return False
		candidates = [ x for x in _servers if x.ping_state and x.ping_state == max_state ]
		server_desc = random.choice(candidates)
		logger.info("Trying to pull data from [%s]", server_desc.address)
		content = Sync._pull(address=server_desc.address)
		if content is None:
			return False
		try:
                        far_data = content['data']
                        far_server_state = data.DataVersion(sequence=content['sequence'], checksum=content['checksum'])
                except (TypeError, KeyError):
                        logger.warning("Cannot parse pulled data from %s", server_desc.address)
			return False
		if data.push_data(other_data=far_data, other_server_state=far_server_state):
			data.save_data()
		return False


	def __call__(self):
		while not self._stop:
			time.sleep(0.05)
			try:
				# Get current state
				self.push_info = data.cur_state()

				if self._try_push_one() or self._try_ping_one():
					_update_servers()
				self._try_pull_one()
			except Exception:
				traceback.print_exc(file=sys.stderr)

	def stop(self):
		# FIXME: lock
		self._stop = True


_sync = Sync()
_thrd = threading.Thread(target=_sync)

def start():
	global _thrd
	_thrd.start()

def stop():
	global _sync, _thrd
	_sync.stop()
	_thrd.join()


_servers = []

_lock = threading.RLock()


def _update_servers():
	global _servers, _servers_copy
	with _lock:
		_servers_copy = copy.deepcopy(_servers)


def _normalize_addr( addr):
	"""Converts the address to the IP:port format.

	Args:
		addr: address to convert
	Returns:
		Converted address or None if invalid.
	"""
	return addr # FIXME: Better checking :-)



cluster_state = ClusterState()

