#!/bin/sh

file="/usr/lib/rpm/pythondistdeps.py"
if [ -w ${file} ]; then
    (set -x; sed -e 's|print(.*PYTHON_EXTRAS_NOT_FOUND_ERROR.*) *$|continue|' -i ${file})
fi
