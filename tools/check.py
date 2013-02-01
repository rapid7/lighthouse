#!/bin/bash

set -e

pychecker --limit 20 tests
pychecker --limit 20 lighthouse

cd lighthouse
pychecker --limit 20 data
pychecker --limit 20 server
pychecker --limit 20 main

