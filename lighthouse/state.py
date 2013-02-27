
class ServerState(object):
	"""
	The state we keep for each server. It consists of serial version number
	and a checksum of the configuration hold.
	"""
	def __init__(self, version = None, checksum=None):
		if version is None or checksum is None:
			raise TypeError() # FIXME: Really TypeError ?
		self.version = int(version)
		self.checksum = checksum

	def __cmp__(self, other):
		"""
		We compare states on version first, then checksum.
		"""
		if other is None:
			return +1

		if self.version > other.version:
			return +1
		elif self.version < other.version:
			return -1

		if self.checksum > other.checksum:
			return +1
		elif self.checksum < other.checksum:
			return -1
		return 0

	def to_dict(self):
		return {
			'version': self.version,
			'checksum': self.checksum,
		}

	def clone(self):
		return ServerState(version=self.version, checksum=self.checksum)

