#!/bin/bash

pychecker --limit 20 tests
pychecker --limit 20 lighthouse

cd lighthouse
for a in *.py ; do
	pychecker --limit 20 $a
done

