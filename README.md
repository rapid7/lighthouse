

Note: This project is under active development. It will be ready soon...


Ligthouse
=========

Ligthouse is a highly-available light-weight in-memory distributed store for
structured data.

Lighthouse provides a simple HTTP interface for load/store operations with
transactional semantics for atomic updates. The structured data may contain
numbers, strings, key-value dictionaries, and arrays. Configuration is further
backed up to disk.

HTTP interface makes it convenient for language implementation as well as easy
use in scripts.



Example configuration
---------------------

Let's have the following configuration:

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

--help		prints usage information and exits
--version	prints version information and exists
--data.d=	path to configuration files which will be loaded upon start
--port=		port we are listening on


Configuration storage
---------------------

Configuration is stored in timestamped files within the ``data.d'' directory.

Upon startup, lighthouse reads the latest non-corrupted configuration in the
data directory.

When a new configuration is uploaded through HTTP interface, it is stored in
a new file in ``data.d'' directory under the new timestamp.


Retrieval of entries
--------------------

Configuration entries are available under the path starting with ``/data/''
Elements in dictionaries are selected by their name. Array entries are selected
by their index in the array.

Data returned are encoded in the JSON format.


Live updates
------------

Updates of the configuration are done in the following way:

1. Acquire a lock
2. Do the changes in /update/
3. Release the lock (Alternatively abort the update)

/data/*
	GET to get configuration

/update/lock_name/*
	PUT
	DELETE

/lock
	GET returns information about the lock
	PUT acquires or releases the lock
	DELETE aborts the update

/version
FIXME



Synchronization proposal
========================


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

