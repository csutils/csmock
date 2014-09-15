#!/bin/sh

find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\n" "$i" | grep "\\.sh$" || head -n1 "$i" | grep "^#!.*sh$"; } >/dev/null && readlink -f "$i" | tee /dev/fd/2; done' \
    | xargs shellcheck --format=gcc \
    | sed 's/$/ <--[shellcheck]/'
