#!/usr/bin/env bash

KEY="$$"

curl -X PUT --data "$KEY" http://172.16.11.103:8001/lock && curl -X PUT --data '{ "file": "/var/log/apache2/access.log", "size": 1024, "XXX": 12345, "providers": { "alpha": ["192.168.1.1", "192.168.1.2"], "beta": ["192.168.2.1", "192.168.2.2"], "gamma": ["192.168.3.1", "192.168.3.2"] } }' "http://172.16.11.103:8001/update/$KEY" && { curl -X PUT http://172.16.11.103:8001/lock/mairead ; curl -X PUT http://172.16.11.103:8001/lock/"$KEY"; }

echo
