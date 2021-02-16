#!/bin/sh

file="/usr/lib/rpm/macros.d/macros.pyproject"
if [ -w ${file} ]; then
    (set -x; sed -e 's|> */dev/stderr|>\&2|' -i ${file})
fi
