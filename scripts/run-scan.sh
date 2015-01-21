#!/bin/sh
SELF="$0"

die() {
    printf "%s: error: %s\n" "$SELF" "$*" >&2
    exit 1
}

warn() {
    printf "%s: warning: %s\n" "$SELF" "$*" >&2
}

RES_DIR="$1"
test -d "$RES_DIR" || die "invalid RES_DIR given: $RES_DIR"

BUILD_CMD="$2"
test -n "$BUILD_CMD" || die "no BUILD_CMD given"

BASE_ERR="$3"
if test -n "$BASE_ERR"; then
    test -r "$BASE_ERR" || die "invalid BASE_ERR given: $BASE_ERR"
fi

# plug cswrap
CSWRAP_LNK_DIR="$(cswrap --print-path-to-wrap)"
test -d "$CSWRAP_LNK_DIR" || die "cswrap not found in \$PATH: $PATH"
export PATH="${CSWRAP_LNK_DIR}:$PATH"
export CSWRAP_CAP_FILE="${RES_DIR}/cswrap-capture.txt"
>"$CSWRAP_CAP_FILE" || die "write failed: $CSWRAP_CAP_FILE"

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
CSCLNG_LNK_DIR="$(csclng --print-path-to-wrap)"
if test -d "$CSCLNG_LNK_DIR"; then
    PATH="${CSCLNG_LNK_DIR}:$PATH"
else
    warn "csclng not found in \$PATH: $PATH"
fi

# plug cscppc (if available)
CSCPPC_LNK_DIR="$(cscppc --print-path-to-wrap)"
if test -d "$CSCPPC_LNK_DIR"; then
    PATH="${CSCPPC_LNK_DIR}:$PATH"
else
    warn "cscppc not found in \$PATH: $PATH"
fi

# run the specified BUILD_CMD
"$SHELL" -xc "$BUILD_CMD"

# check for possible build failure
test "$?" = 0 || exit 125

# process the resulting capture
CURR_ERR="${RES_DIR}/current.err"
csgrep --quiet --event 'error|warning' \
    --path "^${PWD}/" --strip-path-prefix "${PWD}/" \
    --remove-duplicates "${CSWRAP_CAP_FILE}" \
    | csgrep --invert-match --path '^ksh-.*[0-9]+\.c$' \
    | csgrep --invert-match --path 'CMakeFiles/CMakeTmp|conftest.c' \
    | csgrep --invert-match --checker CLANG_WARNING --event error \
    | csgrep --invert-match --checker CLANG_WARNING \
        --msg 'Value stored to '.*' is never read' \
    | csgrep --invert-match --checker CPPCHECK_WARNING \
        --event 'preprocessorErrorDirective|syntaxError' \
    | cssort --key=path >"$CURR_ERR"

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
