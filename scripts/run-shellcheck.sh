#!/bin/sh
export LC_ALL="C"

find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\\n" "$i" | grep -E "^.*\\.(ash|bash|bats|dash|ksh|sh)$" \
        || head -n1 "$i" | grep --text -E "^\\s*((\\#|\\!)|(\\#\\s*\\!)|(\\!\\s*\\#))\\s*(\\/usr(\\/local)?)?\\/bin\\/(env\\s+)?(ash|bash|bats|dash|ksh|sh)\\b"
        } >/dev/null && readlink -f "$i"; done' "$0" \
    | grep -v '^/builddir/build/BUILDROOT/[^/]\+/usr/share/dirsrv/script-templates/' \
    | grep -Ev '^/builddir/build/BUILDROOT/[^/]+/usr/share/systemtap/(examples|testsuite)/' \
    | sort -V | tee /dev/fd/2 \
    | xargs -r shellcheck --format=gcc \
    | sed 's/$/ <--[shellcheck]/' \
    | tee /dev/fd/2
