#!/bin/bash

script="/usr/lib/rpm/redhat/brp-mangle-shebangs"
if [ -x $script ]; then
    (set -x; sed -e 's/fail=1/fail=0/' -i $script )
fi

# skip RPM scripts running in %install that are not needed and break scans
for script in /usr/lib/rpm/{redhat/brp-llvm-compile-lto-elf,brp-strip-static-archive}; do
    if [ -f "$script" ]; then
        ln -fsvT /bin/true "$script"
    fi
done
