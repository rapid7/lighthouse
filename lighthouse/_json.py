#!/usr/bin/python

try:
	import json
except ImportError:
	import simplejson as json

loads = json.loads
dumps = json.dumps

