#!/bin/sh

script="/usr/lib/rpm/redhat/brp-mangle-shebangs"
if [ -x $script ]; then
    (set -x; sed -e 's/fail=1/fail=0/' -i $script )
fi

script="/usr/lib/rpm/brp-strip-static-archive"
if [ -f $script ]; then
    ln -sfvT /bin/true $script
fi
