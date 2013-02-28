
# System imports
import logging

# Local imports
import inlock


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
		# Check that we are not trying to add ourselves
		if addr == self.me:
			return True
		# Check that the address is not in our list already
		if any( [addr == x.address for x in self.instance_monitors]):
			return True

		# Create a new state for the instance
		# Instantiate and start a monitor
		monitor = monitor.Monitor( addr)
		monitor.start()
		self.instance_monitors.append( monitor)

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

# State of the whole cluster
cluster_state = None

def init_cluster_state( me):
	"""Initializes the whole cluster state. """
	global cluster_state
	cluster_state = ClusterState( me)

