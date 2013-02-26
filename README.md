

Note: This project is under active development. It will be ready soon...


Ligthouse
=========

Ligthouse is a highly-available light-weight in-memory distributed store for
structured data.

Lighthouse provides a simple but powerful HTTP/JSON interface for load/store
operations with transactional semantics for atomic updates. The structured data
may contain numbers, strings, key-value dictionaries, and arrays. Data is
further backed up to disk.

It has been developed with aim to provide configuration settings for software
components deployed in distributed systems. HTTP interface makes it convenient
for language-specific interface implementation as well as easy use in shell
scripts and a command line.

Main benefits are:

- highly available (in contrast with standard DB)
- light-weight (in contrast with distributed DB)
- works (in contrast with just anything else)


Example data store
------------------

Let's have following structured data:

    {
      "file": "/var/log/apache2/access.log",
      "size": 1024,
      "providers": {
    	"alpha": ["192.168.1.1", "192.168.1.2"],
    	"beta": ["192.168.2.1", "192.168.2.2"],
    	"gamma": ["192.168.3.1", "192.168.3.2"]
      }
    }

The configuration above is available via HTTP GET command in the ``/data''
folder. For instance, using curl:

    $ curl http://localhost:8001/data/file
    "/var/log/apache2/access.log"
    $ curl http://localhost:8001/data/size
    1024
    $ curl http://localhost:8001/data/providers/beta
    [
      "192.168.2.1", 
      "192.168.2.2"
    ]
    $ curl http://localhost:8001/data/providers/beta/0
    "192.168.2.1"


Command line options
--------------------

--help
  Prints usage information and exits

--version
  Prints version information and exists

--data.d=
   Path where data store snapshots are and will be stored.

--port=
   The port we are listening on.

--seends=
   A comma-separated list of other Lighthouse instances. The list does not have
   to be complete. Instances provided are used for initial bootstrapping.


Configuration storage
---------------------

Configuration is stored in timestamped files within the ``data.d'' directory.

Upon startup, lighthouse reads the latest non-corrupted configuration in the
data directory.

When a new configuration is uploaded through HTTP interface, it is stored in
a new file in ``data.d'' directory under the new timestamp.


Server directory structure
--------------------------

The server communicates via HTTP commands GET, PUT, and DELETE. The basic
structure is:

/data/*
	Contains the current data store

/update/lock_name/*
	After lock acquire contains an updated version of the data store

/lock
	Contains or sets the currect lock

/version
FIXME

/data/[path/to/entry]
	Contains the latest store version
	GET to retrieve a particular store entry
	responds 200 (ok) or 404 (not found)

/update/lock_name/[path/to/entry]
	After lock acquire contains an updated version of the whole data store
	GET to retrieve particular entry of the updated store
	PUT to set particular entry with one command
	DELETE to remove the particular entry

/lock
	GET returns information about the current lock
	PUT acquires or releases the lock
	DELETE aborts the update

/version
FIXME


Retrieval of data entries /data/
--------------------------------

Current store entries are available under the path starting with ``/data/''
Elements in dictionaries are selected by their name. Array entries are selected
by their index in the array.

Data returned are encoded in the JSON format.

If successful, GET returns 200. If the entry does not work, 404 is returned.

Examples:
/data/
	retrieve the whole data store
/data/api/ip
	retrieves an IP address in api


Live updates
------------

To update the store atomically, follow these steps:

1. Acquire a lock
2. Do the changes in /update/
3. Release the lock (alternatively abort the update)

New configuration is automatically propagated to all instances.

Transactions are lock-based. If you want to update the configuration in a
predictable way, do the following:

- acquire lock of one particular instance (for example the one with highest ordering) and update only this one
- acquire lock of N first instances in instance ordering


Acquiring lock /lock/
---------------------

Lock is available at /lock/.

GET operation on /lock/ returns name of the current lock or 404 (not found) if
no lock is acquired

PUT operation acquires a lock with the given name. Returns 200 (ok) if
successful, 403 (forbidden) if a lock is already acquired.

DELETE operation aborts the transaction. Returns 200 if successful or 403 if no
lock is acquired.


Updating configuration ``/update/lock_name/''
-----------------------------------------

When a lock is acquired, a new copy (update store) of the current version is
created. This copy is available at ``/update/lock_name/''.

To retrieve data from the updated store during transaction issue GET operation
to /update/lock_name/ in a similar manner as for current version in /data/.

PUT operation replaces entries at the position given. The position must exists,
otherwise 404 (not found)is returned. New entries must be JSON encoded.

DELETE operation removes all entries from the update store at the position
given. The position must exists, otherwise 404 (not found) is returned.


Synchronization proposal
------------------------


Versioning
----------

Every configuration is versioned. The version consists of

- a sequence number
- a configuration checksum

Configuration with higher sequence version is considered to be newer.
Configurations with the same sequence numbers are compared based on their
checksums. Configurations having the same sequence number and checksum are
considered to be the same.


Cluster
-------

Every instance keeps a list of other instances it sees. For every instance it keeps:

- IP address
- configuration version
- timestamp of last configuration update

This information is periodically refreshed (pull).

Every new configuration version is actively pushed to all other instances with
older configuration.

Bootstraping
------------

Upon start, the instance is trying to join the current cluster and refresh its
configuration. The instance it inactive until the configuration is refreshed.

The instance is trying to locate other instances via:

- old list of instances stored in the configuration
- list of seeds provided on the command line (--seeds)

If there's no need to join the cluster, provide the --bootstrap parameter.

