#!/bin/sh

if [ -x /usr/bin/texhash ]; then
    (set -x; /usr/bin/texhash)
fi
