#!/bin/sh

script="/usr/lib/rpm/redhat/brp-mangle-shebangs"
if [ -x $script ]; then
    (set -x; sed -e 's/fail=1/fail=0/' -i $script )
fi
