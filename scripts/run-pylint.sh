#!/bin/bash
# shellcheck disable=SC2317

export LC_ALL="C"

# this output format was used by Prospector
export MSG_TEMPLATE='{abspath}:{line}:{column}: {msg_id}[pylint]: {msg}'

# implementation of the script that filters python scripts
filter_python_scripts() {
    for i in "$@"; do
        # match by file name suffix
        if [[ "$i" =~ ^.*\.py$ ]]; then
            echo "$i"
            echo -n . >&2
            continue
        fi

        # match by shebang (executable files only)
        RE_SHEBANG='^#!.*python[0-9.]*'
        if test -x "$i" && head -n1 "$i" | grep -q --text "$RE_SHEBANG"; then
            echo "$i"
            echo -n . >&2
        fi
    done
}

# store a script that filters python scripts to a variable
FILTER_SCRIPT="$(declare -f filter_python_scripts)
filter_python_scripts"' "$@"'

# find all python scripts and run pylint on them
echo -n "Looking for python scripts..." >&2
find "$@" -type f -print0 \
    | xargs -0 /bin/bash -c "$FILTER_SCRIPT" "$0" \
    | { sort -uV && echo " done" >&2; } \
    | xargs -r /bin/bash -xc 'pylint -rn --msg-template "${MSG_TEMPLATE}" "$@"' "$0" \
    | grep --invert-match '^\** Module '

# propagage the exit status from the second xargs
exit "${PIPESTATUS[3]}"
