#!/bin/bash

# TODO: Send upstream a formatter to ouput pylint-like output?

# $1 positional argument is security level definition
SEC_LEVEL=$1
TARGET_PATH=${@:2:$#}

# Debug
echo "[DEBUG]	SEC_LEVEL = $SEC_LEVEL" >&2
echo "[DEBUG]	TARGET_PATH = $TARGET_PATH" >&2

if [[ -z "${SEC_LEVEL// }" ]]; then
	echo "[ERROR]	SEC_LEVEL parameter is empty"
elif [[ -z "${SEC_LEVEL// }" ]]; then
	echo "[ERROR]	TARGET_PATH parameter is empty"
fi

# Make sure path to bandit is present in $PATH
export PATH="/usr/local/bin/:$PATH"

# Find all python files and run bandit analysis 
find "$TARGET_PATH" -type f -print0 \
    | xargs -0 sh -c 'for i in "$@"; do { printf "%s\n" "$i" | grep "\\.py\$" \
        || head -n1 "$i" | grep "^#!.*python"
        } >/dev/null && readlink -f "$i"; done' "$0"\
    | sort -V | tee /dev/fd/2 \
    | xargs -r bandit -n -1 -r $SEC_LEVEL --format custom \
    | tee /dev/fd/2
