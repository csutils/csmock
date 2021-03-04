#!/bin/sh
export LC_ALL="C"

find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\n" "$i" | grep "\\.sh\$" \
        || head -n1 "$i" | grep --text -Ev "(atf-|tcl|wi)sh\$" | grep --text "^#!.*sh\$"
        } >/dev/null && readlink -f "$i"; done' "$0" \
    | grep -v '^/builddir/build/BUILDROOT/[^/]\+/usr/share/dirsrv/script-templates/' \
    | sort -V | tee /dev/fd/2 \
    | xargs -r shellcheck --format=gcc \
    | sed 's/$/ <--[shellcheck]/' \
    | tee /dev/fd/2
