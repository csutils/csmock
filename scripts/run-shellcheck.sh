#!/bin/bash
export LC_ALL="C"

# how many shell scripts we pass to shellcheck at a time
export SC_BATCH=1

# how many shellcheck processes we run in parallel
SC_JOBS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
export SC_JOBS

# how long we wait (wall-clock time) for a single shellcheck process to finish
export SC_TIMEOUT=30

# directory for shellcheck results
test -n "$SC_RESULTS_DIR" || export SC_RESULTS_DIR="./shellcheck-results"

# create the directory for shellcheck results and check we can write to it
mkdir "${SC_RESULTS_DIR}" || exit $?
touch "${SC_RESULTS_DIR}/empty.json" || exit $?

# implementation of the script that filters shell scripts
filter_shell_scripts() {
    for i in "$@"; do
        # match by file name suffix
        if [[ "$i" =~ ^.*\.(ash|bash|bats|dash|ksh|sh)$ ]]; then
            echo "$i"
            echo -n . >&2
            continue
        fi

        # match by shebang (executable files only)
        RE_SHEBANG='^\s*((#|!)|(#\s*!)|(!\s*#))\s*(/usr(/local)?)?/bin/(env\s+)?(ash|bash|bats|dash|ksh|sh)\b'
        if test -x "$i" && head -n1 "$i" | grep -qE --text "$RE_SHEBANG"; then
            echo "$i"
            echo -n . >&2
        fi
    done
}

# store a script that filters shell scripts to a variable
FILTER_SCRIPT="$(declare -f filter_shell_scripts)
filter_shell_scripts"' "$@"'

# function that creates a separate JSON file if shellcheck detects anything
wrap_shellcheck() {
    dst="${SC_RESULTS_DIR}/sc-$$.json"
    (set -x && timeout "${SC_TIMEOUT}" shellcheck --format=json1 "$@" > "$dst")
    EC=$?
    case $EC in
        0)
            # no findings detected -> remove the output file
            rm -f "$dst"
            ;;

        1)
            # findings detected -> successful run
            return 0
            ;;

        *)
            # propagate other errors
            return $EC
            ;;
    esac
}

# store a script that filters shell scripts to a variable
SC_WRAP_SCRIPT="$(declare -f wrap_shellcheck)
wrap_shellcheck"' "$@"'

# find all shell scripts and run shellcheck on them
echo -n "Looking for shell scripts..." >&2
find "$@" -type f -print0 \
    | xargs -0 /bin/bash -c "$FILTER_SCRIPT" "$0" \
    | { sort -uV && echo " done" >&2; } \
    | xargs -rn "${SC_BATCH}" --max-procs="${SC_JOBS}" \
    /bin/bash -c "$SC_WRAP_SCRIPT" "$0"
