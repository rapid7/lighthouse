#!/usr/bin/python

SERVER = 'localhost:8001'
BASE_URL = 'http://'+SERVER
LOCKCODE = 'mylock'
LOCKCODE2 = 'mylock2'


import sys
import httplib
import urllib
import urllib2

def block( msg):
	print
	print msg
	print

def die( op, url, msg):
	print
	print '%s  %s %s'%(op, url, msg)
	sys.exit( 1)


def get( url, status, expected=None):
	f = urllib.urlopen( BASE_URL+url)
	data = f.read()
	f.close()
	data_cmp = data.replace( ' ', '').replace( '\n', '')

	if f.getcode() != status:
		die( 'GET', url, 'Status mishmash: %s, expected %s'%( f.getcode(), status))
	if not expected is None and data_cmp != expected:
		print len(expected), len(data)
		die( 'GET', url, 'Content mishmash:"%s", expected "%s"'%( data_cmp, expected))
	print 'GET  %s  %s -> %s'%(url, f.getcode(), data.replace('\n', '').replace('  ', ''))

def put( url, data, status):
	connection =  httplib.HTTPConnection( SERVER)
	connection.request('PUT', url, data)
	f = connection.getresponse()

	if f.status != status:
		die( 'PUT', url, 'Status mishmash: %s, expected %s'%( f.status, status))
	print 'PUT  %s %s  %s'%(url, data, f.status)

def delete( url, status):
	connection =  httplib.HTTPConnection( SERVER)
	connection.request('DELETE', url, '')
	f = connection.getresponse()
	resp = f.read()

	if f.status != status:
		die( 'DELETE', url, 'Status mishmash: %s, expected %s'%( f.status, status))
	print 'DELETE  %s  %s -> %s'%(url, f.status, resp)


#
# Lighthouse is uninitialized as started
#

block( 'Get elements')

get( '/', 200)                 # Root returns info
get( '//', 404)                # Root is not in doubleslash
get( '/foo', 404)              # Invalid address
get( '/foo/', 404)             # Invalid address
get( '/data', 200)             # There are no data
get( '/data/', 200)            # There are no data
get( '/data/foo', 404)         # Invalid resource, no data
get( '/data/foo/', 404)        # Invalid resource, no data
get( '/update', 404)           # No update, lock is not acquired
get( '/update/', 404)          # No update, lock is not acquired
get( '/update/foo', 403)       # Lock is not acquired, forbidden
get( '/update/foo/', 403)      # Lock is not acquired, forbidden
get( '/lock', 404)             # There is no lock
get( '/lock/', 404)            # There is no lock
get( '/lock/foo', 404)         # Invalid resource under the lock

block( 'Delete elements')

delete( '/', 403)              # Cannot delete root
delete( '/foo', 404)           # Resource does not exist
delete( '/foo/', 404)          # Resource does not exist
delete( '/data', 403)          # Invalid address, missing slash
delete( '/data/', 403)         # Cannot delete data
delete( '/data/foo', 404)      # Invalid resource, no data
delete( '/update', 404)        # No update, lock is not acquired
delete( '/update/', 404)       # No update, lock is not acquired
delete( '/update/foo', 403)    # Lock is not acquired, forbidden
delete( '/lock', 404)          # There is no lock, cannot remove it
delete( '/lock/', 404)         # There is no lock, cannot remove it
delete( '/lock/fsd', 404)      # Invalid resource under the lock

block( 'Submit data')

put( '/', '', 403)             # Forbidden to put to root
put( '/foo', '', 404)          # Invalid URL
put( '/foo/', '', 404)         # Invalid URL
put( '/data', '', 403)         # Invalid URL, missing slash
put( '/data/', '', 403)        # Forbidden for data
put( '/data/foo', '', 404)     # Resouce not found
put( '/update', '', 404)       # Update does not exist, lock not acquired
put( '/update/', '', 404)      # Update does not exist, lock not acquired
put( '/update/foo', '', 403)   # Update forbidden, lock not acquired
put( '/update/foo/', '', 403)  # Update forbidden, lock not acquired
put( '/lock/foo', '', 404)     # Resouce not found
put( '/lock/foo/', '', 404)    # Resouce not found
put( '/lock/', '', 404)        # Cannot abort if there is no lock
put( '/lock/', LOCKCODE, 200)  # Acquire lock

#
# Lock is acquired
#

block( 'Some basic tests to ensure all is ok')

get( '/lock/', 200, LOCKCODE)          # Return lock
get( '/lock/foo', 404)                 # Invalid resource under the lock
get( '/update/', 404)                  # Update requires lock name
get( '/update/'+LOCKCODE, 200, '{}')   # Update contains empty data
get( '/update/foo', 403)               # Not a lock's name
get( '/update/foo/', 403)              # Not a lock's name
get( '/update/'+LOCKCODE+'/foo', 404)  # Unknown field
get( '/update/'+LOCKCODE+'/foo/', 404) # Unknown field

block( 'Reacquire the lock')

put( '/lock/', LOCKCODE, 200)   # Acquiring the same lock is idempotent
put( '/lock/', LOCKCODE2, 403)  # Forbidden, lock acquired

block( 'Updates')

put( '/update/'+LOCKCODE+'/', '""', 201)	# Empty string
get( '/update/'+LOCKCODE+'/', 200, '""')
put( '/update/'+LOCKCODE+'/', '"a"', 201)	# Just string
get( '/update/'+LOCKCODE+'/', 200, '"a"')
put( '/update/'+LOCKCODE+'/', '10', 201)	# Number
get( '/update/'+LOCKCODE+'/', 200, '10')
put( '/update/'+LOCKCODE+'/', '{}', 201)	# Empty dict
get( '/update/'+LOCKCODE+'/', 200, '{}')
put( '/update/'+LOCKCODE+'/', '{"a":1,"b":"2","c":""}', 201) # Dict
get( '/update/'+LOCKCODE+'/', 200, '{"a":1,"b":"2","c":""}')
get( '/update/'+LOCKCODE+'/a', 200, '1')
get( '/update/'+LOCKCODE+'/a/', 200, '1')
get( '/update/'+LOCKCODE+'/b', 200, '"2"')
get( '/update/'+LOCKCODE+'/b/', 200, '"2"')
get( '/update/'+LOCKCODE+'/c', 200, '""')
get( '/update/'+LOCKCODE+'/c/', 200, '""')
get( '/update/'+LOCKCODE+'/d', 404)           # Does not exist
get( '/update/'+LOCKCODE+'/d/', 404)          # Does not exist
put( '/update/'+LOCKCODE+'/d', '3', 201)      # Extend the current dict with a number
get( '/update/'+LOCKCODE+'/d', 200, '3')
put( '/update/'+LOCKCODE+'/e', '{"q":"w"}', 201) # Extend the current dict with a dict
get( '/update/'+LOCKCODE+'/e', 200, '{"q":"w"}')

# TODO: check arrays and adding at the end of an array, plus deletion

delete( '/update/'+LOCKCODE+'/a', 204)        # Delete entry a
get( '/update/'+LOCKCODE+'/a', 404)           # Make sure it does not exist anymore
delete( '/update/'+LOCKCODE+'/b/', 204)       # Delete entry b
get( '/update/'+LOCKCODE+'/b', 404)           # Make sure it does not exist anymore
get( '/update/'+LOCKCODE+'/', 200, '{"c":"","d":3,"e":{"q":"w"}}')

block( 'Release lock')

put( '/lock/'+LOCKCODE, '', 200)  # The lock is released and data updated are active now
put( '/lock/'+LOCKCODE, '', 404)  # Released again, the lock does not exist

#
block( 'Initialized, lock released')
#

block( 'Check that we are in a normal state again')

get( '/update/', 404)
get( '/lock/', 404)

block( 'Check data content')

get( '/data/', 200, '{"c":"","d":3,"e":{"q":"w"}}')
get( '/data/c', 200, '""')
get( '/data/d', 200, '3')
get( '/data/e', 200, '{"q":"w"}')
get( '/data/e/q', 200, '"w"')
get( '/data/e/w', 404)

#
block( 'Check that "data" is copied to "update" after the lock is acquired')
#

get( '/data/e/q', 200, '"w"')
put( '/lock/', LOCKCODE, 200)                 # Acquire lock
get( '/data/e/q', 200, '"w"')                 # It is in data/
get( '/update/'+LOCKCODE+'/e/q', 200, '"w"')  # It is in update/
put( '/lock/'+LOCKCODE, '', 200)               # Release lock
get( '/data/e/q', 200, '"w"')                 # It is still in data
get( '/update/'+LOCKCODE+'/e/q', 403)         # Make sure update/ is removed

#
block( 'Test aborting the update')
#

put( '/lock/', LOCKCODE, 200)    # Acquire lock
get( '/data/e/q', 200, '"w"')    # Make sure data got copied
get( '/update/'+LOCKCODE+'/e/q', 200, '"w"')  # Make sure data got copied
delete( '/update/'+LOCKCODE+'/e/q', 204)      # Delete one field
delete( '/lock/'+LOCKCODE, 200)           # Abort the transaction
get( '/data/e/q', 200, '"w"')    # Make sure data is still there

#
block( 'Test push/pull copy and state')
#

# Read the configuration
C = '{"data":{"c":"","d":3,"e":{"q":"w"}},"version":{"checksum":"9635212a5b654e8efff3e81475c1aa69","sequence":2}}'
S = '{"cluster":[],"version":{"checksum":"9635212a5b654e8efff3e81475c1aa69","sequence":2}}'
get( '/copy/', 200, C)
get( '/state/', 200, S)
# Put copy with the same version - should be ignored
put( '/copy/', C, 201)
get( '/copy/', 200, C)
get( '/state/', 200, S)
# Put copy with newer sequence - should be accepted
C = '{"data":{"c":"","d":3,"e":{"q":"w"}},"version":{"checksum":"9635212a5b654e8efff3e81475c1aa69","sequence":6}}'
S = '{"cluster":[],"version":{"checksum":"9635212a5b654e8efff3e81475c1aa69","sequence":6}}'
put( '/copy/', C, 201)
get( '/copy/', 200, C)
get( '/state/', 200, S)


print
print 'All tests passed'

