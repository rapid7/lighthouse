
class DataVersion(object):
	"""
	The state we keep for each server. It consists of serial sequence number
	and a checksum of the configuration hold.
	"""
	def __init__(self, sequence = None, checksum=None):
		if sequence is None or checksum is None:
			raise TypeError() # FIXME: Really TypeError ?
		self.sequence = int(sequence)
		self.checksum = checksum

	def __cmp__(self, other):
		"""
		We compare states on sequence first, then checksum.
		"""
		if other is None:
			return +1

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

	def clone(self):
		return DataVersion(sequence=self.sequence, checksum=self.checksum)

