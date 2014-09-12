#!/bin/sh

find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do head -n1 "$i" | grep "^#!.*python" >/dev/null && readlink -f "$i"; done' \
    | xargs pylint -rn --msg-template '{abspath}:{line}:{column}: {msg_id}[pylint]: {msg}'
