
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
import state
import data

logger = logging.getLogger(__name__)

class ServerDesc(object):
	"""
	Describes current state of the Lighthouse instance as seen from the
	current instance.
	"""

	def __init__(self, address):
		# Address as a string of the form ip:port or host:port
		self.address = address
		# Last state that was pushed to the server (instance of State or None)
		self.uploaded_state = None
		# Last state of the server received by ping (instance of State or None)
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
		server_desc.ping_state = state.DataVersion(sequence=info['sequence'], checksum=info['checksum'])
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
                        far_server_state = state.DataVersion(sequence=content['sequence'], checksum=content['checksum'])
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
_servers_copy = []


def _update_servers():
	global _servers, _servers_copy
	with _lock:
		_servers_copy = copy.deepcopy(_servers)

def get_servers_status():
	ret = []
	with _lock:
		ret = [x.to_dict() for x in _servers_copy]
	return data.dump_json(ret)


def _process_address(address):
	return address # FIXME: Better checking :-)


def add_servers(new_servers):
	global _servers, _lock
	with _lock:
		for server in new_servers:
			addr = _process_address(server)
			if any([ addr == x.address for x in _servers ]):
				continue
			_servers.append(ServerDesc(address=addr))
		_update_servers()

