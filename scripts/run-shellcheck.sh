#!/bin/sh
export LC_ALL="C"

find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\n" "$i" | grep "\\.sh\$" \
        || head -n1 "$i" | grep -Ev "(tcl|wi)sh\$" | grep "^#!.*sh\$"
        } >/dev/null && readlink -f "$i"; done' \
    | sort -V | tee /dev/fd/2 \
    | xargs -r shellcheck --format=gcc \
    | sed 's/$/ <--[shellcheck]/' \
    | tee /dev/fd/2
