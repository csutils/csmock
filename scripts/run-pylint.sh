#!/bin/sh
export LC_ALL="C"

find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\n" "$i" | grep "\\.py\$" \
        || head -n1 "$i" | grep --text "^#!.*python"
        } >/dev/null && readlink -f "$i"; done' "$0" \
    | sort -V | tee /dev/fd/2 \
    | xargs -r pylint -rn --msg-template '{abspath}:{line}:{column}: {msg_id}[pylint]: {msg}' \
    | grep --invert-match '^\** Module ' \
    | tee /dev/fd/2
