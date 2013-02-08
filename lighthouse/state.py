import data

class ServerState(object):
	def __init__(self, version = None, checksum=None):
		if version is None or checksum is None:
			raise TypeError() # FIXME: Really TypeError ?
		self.version = int(version)
		self.checksum = checksum

	def __cmp__(self, other):
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
			'checksum':self.checksum,
		}

	def clone(self):
		return ServerState(version=self.version, checksum=self.checksum)
