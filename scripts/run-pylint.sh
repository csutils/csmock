#!/bin/sh

find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\n" "$i" | grep "\\.py$" || head -n1 "$i" | grep "^#!.*python"; } >/dev/null && readlink -f "$i" | tee /dev/fd/2; done' \
    | xargs pylint -rn --msg-template '{abspath}:{line}:{column}: {msg_id}[pylint]: {msg}'
