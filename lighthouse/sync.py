
# System imports
import logging

# Local imports
import inlock
import helpers


logger = logging.getLogger(__name__)


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
	def add_instance( self, addr):
		"""Adds a new instance to the cluster.

		New asynchronous monitor is created.

		Args:
			addr: address in the form of ip:port or host:port
		"""
		# Check that we are not trying to add ourselves
		if addr == self.me:
			return
		# Check that the address is not in our list already
		if any( [addr == x.address for x in self.instance_monitors]):
			return

		# Create a new state for the instance
		# Instantiate and start a monitor
		mon = monitor.Monitor( addr)
		mon.start()
		self.instance_monitors.append( mon)

	@inlock.synchronized
	def get_state(self):
		"""Returns state of the cluster.
		"""
		return [x.to_dict() for x in self.instance_monitors]

	@inlock.synchronized
	def force_push(self):
		"""Force all monitors to send update.
		"""
		for monitor in self.instance_monitors:
			monitor.force_push.set()

	def update_state(self, cstate):
		"""Accepts all new instances in the state given.
		"""
		for state in cstate:
			self.add_instance( state['address'])

	def update_state_json(self, content):
		try:
			cstate = helpers.load_json( content)[ 'cluster']
			self.update_state( cstate)
		except (ValueError, KeyError):
			return False
		return True

# State of the whole cluster
cluster_state = None

def init_cluster_state( me):
	"""Initializes the whole cluster state. """
	global cluster_state
	cluster_state = ClusterState( me)

