#!/bin/sh
SELF="$0"

msg() {
    printf "\n%s: %s\n" "$SELF" "$*" >&2
}

die() {
    msg "error: %s" "$*"
    exit 1
}

warn() {
    msg "warning: %s" "$*"
}

warn_not_in_path() {
    warn "$1 not found in \$PATH: $PATH"
}

RES_DIR="$1"
test -d "$RES_DIR" || die "invalid RES_DIR given: $RES_DIR"

BUILD_CMD="$2"
test -n "$BUILD_CMD" || die "no BUILD_CMD given"

FILTER_CMD="$3"
test -n "$FILTER_CMD" || FILTER_CMD=cat

BASE_ERR="$4"
if test -n "$BASE_ERR"; then
    test -r "$BASE_ERR" || die "invalid BASE_ERR given: $BASE_ERR"
fi

# plug cswrap
CSWRAP_LNK_DIR="$(cswrap --print-path-to-wrap)"
test -d "$CSWRAP_LNK_DIR" || die "cswrap not found in \$PATH: $PATH"
export PATH="${CSWRAP_LNK_DIR}:$PATH"
export CSWRAP_CAP_FILE="${RES_DIR}/cswrap-capture.txt"
true >"$CSWRAP_CAP_FILE" || die "write failed: $CSWRAP_CAP_FILE"

if test -z "$CSWRAP_DEL_CFLAGS" && test -z "$CSWRAP_DEL_CXXFLAGS" \
    && test -z "$CSWRAP_ADD_CFLAGS" && test -z "$CSWRAP_ADD_CXXFLAGS"
then
    # use the default GCC flags overrides
    export CSWRAP_DEL_CFLAGS="-Werror:-fdiagnostics-color:-fdiagnostics-color=always"
    export CSWRAP_DEL_CXXFLAGS="$CSWRAP_DEL_CFLAGS"
    export CSWRAP_ADD_CXXFLAGS="-Wall:-Wextra"
    export CSWRAP_ADD_CFLAGS="$CSWRAP_ADD_CFLAGS:-Wno-unknown-pragmas"
fi

# plug csclng (if available)
msg "Looking for csclng..."
CSCLNG_LNK_DIR="$(csclng --print-path-to-wrap)"
if test -d "$CSCLNG_LNK_DIR"; then
    if (set -x; clang --version); then
        PATH="${CSCLNG_LNK_DIR}:$PATH"
    else
        warn_not_in_path clang
    fi
else
    warn_not_in_path csclng
fi

# plug cscppc (if available)
msg "Looking for cscppc..."
CSCPPC_LNK_DIR="$(cscppc --print-path-to-wrap)"
if test -d "$CSCPPC_LNK_DIR"; then
    if (set -x; cppcheck --version); then
        PATH="${CSCPPC_LNK_DIR}:$PATH"
    else
        warn_not_in_path cppcheck
    fi
else
    warn_not_in_path cscppc
fi

# plug Coverity Analysis (if available in $PATH)
msg "Looking for Coverity Analysis..."
BUILD_CMD_WRAP=
COV_INT_DIR=
if (set -x; cov-build --ident && cov-analyze --ident && cov-format-errors --ident)
then
    COV_INT_DIR="${RES_DIR}/cov"
    BUILD_CMD_WRAP="cov-build --dir=${COV_INT_DIR}"
fi

# run the specified BUILD_CMD
msg "Running the build!"
(set -x; $BUILD_CMD_WRAP "$SHELL" -xc "$BUILD_CMD")

# check for possible build failure
test "$?" = 0 || exit 125

# process the resulting capture
RAW_CURR_ERR="${RES_DIR}/raw-current.err"
(set -x; csgrep --quiet --event 'error|warning' \
    --remove-duplicates "${CSWRAP_CAP_FILE}" \
    | csgrep --invert-match --checker CLANG_WARNING --event error \
    | csgrep --invert-match --checker CLANG_WARNING \
        --msg "Value stored to '.*' is never read" \
    | csgrep --invert-match --checker CPPCHECK_WARNING \
        --event 'preprocessorErrorDirective|syntaxError' \
    > "$RAW_CURR_ERR")

# run Coverity Analysis (if anything has been captured)
if test -n "$COV_INT_DIR" && test -e "${COV_INT_DIR}/emit/"*/emit-db.write-lock
then
    msg "Running Coverity Analysis..."
    (set -x; cov-analyze "--dir=${COV_INT_DIR}" --security --concurrency \
        && cov-format-errors "--dir=${COV_INT_DIR}" --emacs-style \
        | csgrep --prune-events=1 >> "$RAW_CURR_ERR")
fi

# process the given filters and sort the results
CURR_ERR="${RES_DIR}/current.err"
(set -x; csgrep --path "^${PWD}/" --strip-path-prefix "${PWD}/" <"$RAW_CURR_ERR" \
    | csgrep --invert-match --path '^ksh-.*[0-9]+\.c$' \
    | csgrep --invert-match --path 'CMakeFiles/CMakeTmp|conftest.c' \
    | cssort --key=path \
    | $FILTER_CMD >"$CURR_ERR")

# compare the results with base (if we got one)
ADDED_ERR="${RES_DIR}/added.err"
FIXED_ERR="${RES_DIR}/fixed.err"
if test -n "$BASE_ERR"; then
    csdiff -z "$BASE_ERR" "$CURR_ERR" > "$ADDED_ERR"
    csdiff -z "$CURR_ERR" "$BASE_ERR" > "$FIXED_ERR"
else
    rm -f "$ADDED_ERR" "$FIXED_ERR"
fi

# return the according exit code
if grep "^Error" "$ADDED_ERR" >/dev/null 2>&1; then
    # new defects found!
    exit 7
else
    exit 0
fi
