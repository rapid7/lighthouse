
# System imports
import logging
import random
import sys
import threading
import time
import traceback

# Local imports
import inlock
import data
import helpers


# Period between pings in seconds
PING_PERIOD = 0.5
# Maximal delay for push/pull operation
REACTION_VAR = 0.01

logger = logging.getLogger(__name__)


class Monitor(threading.Thread):
	"""Monitors the instance given for updates.

	Runs in its own thread. It follows the ping/pull/push pattern.

	Information about monitored instance is accessed cuncurrently by a
	thread collecting states of all instances.

	Public instance attributes:
		address: address of the monitored instance, immutable
	"""

	def __init__(self, address):
		"""Initializes the monitor with instance state given.

		Args:
			address: address of the instance to monitor
		"""
		# Initialize the thread as daemon
		super(Monitor, self).__init__(name="Monitor %s"%address)
		self.setDaemon( True)
		inlock.add_lock( self)
			
		# Asynchronous communicaton - push request
		self.force_push = threading.Event()
			
		# Instance information
			
		# Address of the instance as a string of the form ip:port or
		# host:port. It is immutable.
		self.address = address
			
		# Last version of the instance data as reported (instance of DataVersion or None)
		self._version = data.DataVersion()
		# If last ping successed
		self._reachable = False
		# Time of the last successful ping (DateTime)
		self._last_reachable = helpers.NOTIME
		# Time of the last successful push (DateTime)
		self._last_push = helpers.NOTIME

	def _push(self):
		"""Tries to push the current data to the other instance. """
		# Check that current configuration is newer than that on the other instance
		xdata = data.cur_data()
		if self._version >= xdata.version:
			return

		# Push data
		logger.info( '%s Push', self.address)
		result = helpers.push( self.address, xdata.dump_json({
				'sequence': xdata.version.sequence,
				'checksum': xdata.version.checksum,
				'data': xdata
			}))

		# Mark time when we tried to push new data
		if result:
			self._touch_last_push()

	def _pull(self):
		# Ping the instance and get its version
		logger.info( '%s Ping', self.address)

		info = helpers.info( self.address)
		if not info:
			self._reachable = False
			return
		try:
			self._version = data.DataVersion( sequence=info[ 'sequence'], checksum=info[ 'checksum'])
		except (TypeError, KeyError):
			logger.error( '%s Invalid pulled data', self.address)
			return
		self._reachable = True
		self._touch_last_reachable()

		# Check that the other instance has newer configuration
		if self._version <= data.cur_data().version:
			return

		# The instance has newer configuration, try to pull it
		logger.info( '%s Pull', self.address)

		content = helpers.pull( self.address)
		if content is None:
			return False
		try:
			far_data = content[ 'data']
			far_version = data.DataVersion( sequence=content[ 'sequence'], checksum=content[ 'checksum'])
		except (TypeError, KeyError):
			logger.error( '%s Invalid pulled data', self.address)
			return

		# Check in new data
		if data.push_data( far_data, far_version):
			data.save_data()

	def _cycle(self):
		"""One update cycle.
		
		It consists of pull or push request.
		"""
		# Wait for push signal or timeout
		do_push = self.force_push.wait( PING_PERIOD)
		# Wait little bit more to avoid update storms
		time.sleep( random.random( REACTION_VAR))
		# Perform the action
		if do_push:
			self._push()
		else:
			self._pull()

	def run(self):
		"""Runs the cycle ping/pull/push.
		"""
		while True:
			try:
				self._cycle()
			except:
				logger.error( 'Unhandled exception %s', sys.exc_info()[0])
				logger.error( '%s', ''.join( traceback.format_tb( sys.exc_info()[2])))
				return False

	@inlock.synchronized
	def _touch_last_push(self):
		self._last_push = helpers.now()

	@inlock.synchronized
	def _touch_last_reachable(self):
		self._last_reachable = helpers.now()

	@inlock.synchronized
	def to_dict(self):
		return {
			'address': self.address,
			'version': self._version.to_dict(),
			'reachable': self.reachable,
			'last-reachable': helpers.dump_time( self._last_reachable),
			'last-push': helpers.dump_time( self._last_push),
		}

class ClusterState:
	"""Describes state of the cluster.
	"""


	def __init__(self, me):
		"""Initializes the cluster state with all entries empty.

		Args:
			me: My address in the form of IP:port
		"""
		# Store my address
		self.me = me
		# All instance monitors
		self.instance_monitors = []
		inlock.add_lock( self)


	@inlock.synchronized
	def add_instance(self, xaddr):
		"""Adds a new instance to the cluster.

		New asynchronous monitor is created.

		Args:
			xaddr: address in the form of ip:port or host:port
		Returns:
			True is successful, False otherwise
		"""
		# Normalize the address
		addr = helpers.normalize_addr( xaddr)
		if not addr:
			return False
		# Chect that we are not trying to add ourselves
		if addr == self.me:
			return True
		# Check that the address is not in our list already
		if any( [addr == x.address for x in self.instance_monitors]):
			return True

		# Create a new state for the instance
		# Instantiate and start a monitor
		monitor = Monitor( addr)
		monitor.start()
		self.instance_monitors.append( monitor)

	@inlock.synchronized
	def get_state(self):
		"""Returns state of the cluster.
		"""
		return [x.to_dict() for x in self.instance_monitors]

# State of the whole cluster
cluster_state = None

def init_cluster_state( me):
	"""Initializes the whole cluster state. """
	global cluster_state
	cluster_state = ClusterState( me)

