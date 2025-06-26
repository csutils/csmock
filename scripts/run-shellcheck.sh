#!/bin/bash
# shellcheck disable=SC2319

export LC_ALL="C"

# how many shell scripts we pass to shellcheck at a time
test -n "$SC_BATCH" || export SC_BATCH=1
test 0 -lt "$SC_BATCH" || exit $?

# how many shellcheck processes we run in parallel
test -n "$SC_JOBS" || SC_JOBS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
export SC_JOBS

# how long we wait (wall-clock time) for a single shellcheck process to finish
test -n "$SC_TIMEOUT" || export SC_TIMEOUT=30
test 0 -lt "$SC_TIMEOUT" || exit $?

# directory for shellcheck results
test -n "$SC_RESULTS_DIR" || export SC_RESULTS_DIR="./shellcheck-results"

# create the directory for shellcheck results and check we can write to it
mkdir "${SC_RESULTS_DIR}" || exit $?
touch "${SC_RESULTS_DIR}/empty.json" || exit $?

# check whether shellcheck supports --format=json1
export SC_RESULTS_{BEG,END}
if shellcheck --help 2>/dev/null | grep -q json1; then
    SC_OPTS=(--format=json1)
    SC_RESULTS_BEG=
    SC_RESULTS_END=
else
    # compatibility workaround for old versions of shellcheck
    SC_OPTS=(--format=json)
    SC_RESULTS_BEG='{"comments":'
    SC_RESULTS_END='}'
fi

# check whether shellcheck supports --external-sources
if shellcheck --help 2>/dev/null | grep -q external-sources; then
    SC_OPTS+=(--external-sources)
fi

# check whether shellcheck supports --source-path
if shellcheck --help 2>/dev/null | grep -q source-path; then
    sp=
    for dir in "$@"; do
        # search path works only for directories
        test -d "$dir" || continue

        # append a single directory from cmd-line args of this script
        sp="${sp}:${dir}"
    done
    if test -n "$sp"; then
        # pass the colon-delimited list of dirs via --source-path to shellcheck
        SC_OPTS+=(--source-path="${sp#:}")
    fi
fi

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
    log="${dst%.json}.log"

    # compatibility workaround for old versions of shellcheck
    echo -n "$SC_RESULTS_BEG" > "$dst"

    (set -x && timeout "${SC_TIMEOUT}" shellcheck "${SC_OPTS[@]}" "$@" >> "$dst" 2> "$log")
    EC=$?

    # compatibility workaround for old versions of shellcheck
    echo -n "$SC_RESULTS_END" >> "$dst"

    case $EC in
        0)
            # no findings detected -> remove the output files
            rm -f "$dst" "$log"
            ;;

        1)
            # findings detected -> successful run
            if [ -n "$(<"$log")" ]; then
                # something printed to stderr -> record an internal error of shellcheck
                sed -re 's|^(shellcheck): ([^:]+): (.*)$|\2: internal error: \3 <--[\1]|' "$log" > "$dst"
            else
                rm -f "$log"
            fi
            return 0
            ;;

        *)
            # propagate other errors
            return $EC
            ;;
    esac
}

# store a script that filters shell scripts to a variable (and explicitly
# propagate the ${SC_OPTS} shell array, which cannot be easily exported)
SC_WRAP_SCRIPT="$(declare -p SC_OPTS)
$(declare -f wrap_shellcheck)
wrap_shellcheck"' "$@"'

# find all shell scripts and run shellcheck on them
echo -n "Looking for shell scripts..." >&2
find "$@" -type f -print0 \
    | xargs -0 /bin/bash -c "$FILTER_SCRIPT" "$0" \
    | { sort -uV && echo " done" >&2; } \
    | xargs -rn "${SC_BATCH}" --max-procs="${SC_JOBS}" \
    /bin/bash -c "$SC_WRAP_SCRIPT" "$0"
