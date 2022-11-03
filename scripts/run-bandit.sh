#!/bin/bash
export LC_ALL="C"

# $1 positional argument is security level definition
SEC_LEVEL=$1
shift

# Debug
echo "[DEBUG]	SEC_LEVEL = $SEC_LEVEL" >&2
echo "[DEBUG]	TARGET_PATH = $*" >&2

if [[ -z "${SEC_LEVEL// }" ]]; then
	echo "[ERROR]	SEC_LEVEL parameter is empty" >&2
	exit 1
elif [[ -z "$*" ]]; then
	echo "[ERROR]	TARGET_PATH parameter is empty" >&2
	exit 1
fi

# Find all python files and run bandit analysis 
find "$@" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\n" "$i" | grep "\\.py\$" \
        || head -n1 "$i" | grep --text "^#!.*python"
        } >/dev/null && readlink -f "$i"; done' "$0" \
    | sort -V | tee /dev/fd/2 \
    | xargs -r bandit -n -1 -r $SEC_LEVEL --format custom \
    | tee /dev/fd/2
