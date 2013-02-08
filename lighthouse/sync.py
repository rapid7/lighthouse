import threading
import time
import sys
import urllib2
import datetime
import copy

import random
import state
import data

class ServerDesc(object):
	def __init__(self, address):
		print >>sys.stderr, ">> [%s]" % address
		self.address = address
		self.uploaded_state = None
		self.ping_state = None
		self.reachable = True
		self.last_ping = None
		self.last_upload = None

	@staticmethod
	def dump_time(time):
		if time is None:
			return None
		return time.strftime("%Y%m%dT%H%M%S")

	@staticmethod
	def dump_state(state):
		if state is None:
			return None
		return state.to_dict()

	def to_dict(self):
		return {
			'address': self.address,
			'uploaded-state':ServerDesc.dump_state(self.uploaded_state),
			'ping-state':ServerDesc.dump_state(self.ping_state),
			'reachable':self.reachable,
			'last-ping':ServerDesc.dump_time(self.last_ping),
			'last-upload':ServerDesc.dump_time(self.last_upload),
		}

class Sync:
	def __init__(self):
		self._stop = False
		self.push_info = {}

	@staticmethod
	def _url(address, path='/'):
		if len(path) < 1 or path[0] != '/':
			raise TypeError()
		return "http://%s%s" % (address, path)

	@staticmethod
	def _push(address, push_content):
		url = Sync._url(address)
		opener = urllib2.build_opener(urllib2.HTTPHandler)
		request = urllib2.Request(url, data=push_content)
		request.add_header('Content-Type', 'application/json')
		request.get_method = lambda: 'PUT'
		try:
			url = opener.open(request)
		except urllib2.URLError as e:
			print >>sys.stderr, "Cannot PUT data to [%s] : %s" % (url, e)
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
			print >>sys.stderr, "Cannot GET data from [%s] : %s" % (url, e)
			return None

	@staticmethod
	def _pull(address):
		return Sync._get(address, "/pull")

	@staticmethod
	def _info(address):
		str_info = Sync._get(address, "/info")
		if str_info is None:
			return None
		return data.load_json(str_info)


	def _try_push_one(self):
		global _servers
		if not data.should_push(self.push_info):
			return False
		push_info_state = self.push_info['state']
		if any([ x.ping_state and push_info_state < x.ping_info_state for x in _servers ]):
			return False
		candidates = [ x for x in _servers if x.state < push_info_state ]
		if 0 == len(candidates):
			return False
		server_desc = random.choice(candidates)
		print >>sys.stderr, "Trying to push data to [%s]" % server_desc.address
		server_desc.uploaded_state = push_info_state
		server_desc.last_upload = datetime.datetime.now()
		if not Sync._push(address=server_desc.address, data=data.dump_json(self.push_info['data'])):
			server.reachable = False
			return True
		return True

	def _try_ping_one(self):
		global _servers
		now = datetime.datetime.now()
		threshold = now - datetime.timedelta(seconds=60)
		candidates = [ x for x in _servers if not x.last_ping or x.last_ping <= threshold ]
		if 0 == len(candidates):
			return False
		server_desc = random.choice(candidates)
		print >>sys.stderr, "Trying to ping [%s]" % server_desc.address
		info = Sync._info(address=server_desc.address)
		server_desc.last_ping = now
		if not info:
			server_desc.reachable = False
			return True
		server_desc.ping_state = state.ServerState(version=info['version'], checksum=info['checksum'])
		return True

	def __call__(self):
		while not self._stop:
			time.sleep(0.05)
			if self._try_push_one() or self._try_ping_one():
				_update_servers()

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

_lock = threading.Lock()
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
	global _servers
	for server in new_servers:
		addr = _process_address(server)
		if any([ addr == x.address for x in _servers ]):
			continue
		_servers.append(ServerDesc(address=addr))
	_update_servers()
