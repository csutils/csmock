#!/bin/sh

if [ -x /usr/bin/update-mime-database ]; then
    (set -x; /usr/bin/update-mime-database -n /usr/share/mime)
fi
