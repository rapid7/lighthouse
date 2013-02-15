#!/usr/bin/env bash

KEY="$$"

curl -X PUT --data "$KEY" http://127.0.0.1:8001/lock && curl -X PUT --data '{ "file": "/var/log/apache2/access.log", "size": 1024, "providers": { "alpha": ["192.168.1.1", "192.168.1.2"], "beta": ["192.168.2.1", "192.168.2.2"], "gamma": ["192.168.3.1", "192.168.3.2"] } }' "http://127.0.0.1:8001/update/$KEY" && curl -X PUT http://127.0.0.1:8001/lock

echo
