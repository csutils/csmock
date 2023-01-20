#!/bin/bash
export LC_ALL="C"

# implementation of the script that filters shell scripts
filter_shell_scripts() {
    for i in "$@"; do
        if [[ "$i" =~ ^.*\.(ash|bash|bats|dash|ksh|sh)$ ]]; then
            readlink -f "$i"
            continue
        fi

        RE_SHEBANG="^\\s*((\\#|\\!)|(\\#\\s*\\!)|(\\!\\s*\\#))\\s*(\\/usr(\\/local)?)?\\/bin\\/(env\\s+)?(ash|bash|bats|dash|ksh|sh)\\b"
        if head -n1 "$i" | grep --text -E "$RE_SHEBANG" >/dev/null; then
            readlink -f "$i"
        fi
    done
}

# store a script that filters shell scripts to a variable
FILTER_SCRIPT="$(declare -f filter_shell_scripts)
filter_shell_scripts"' "$@"'

find "$@" -type f -print0 \
    | xargs -0 /bin/bash -c "$FILTER_SCRIPT" "$0" \
    | grep -v '^/builddir/build/BUILDROOT/[^/]\+/usr/share/dirsrv/script-templates/' \
    | grep -Ev '^/builddir/build/BUILDROOT/[^/]+/usr/share/systemtap/(examples|testsuite)/' \
    | sort -V | tee /dev/fd/2 \
    | xargs -r shellcheck --format=gcc \
    | sed 's/$/ <--[shellcheck]/' \
    | tee /dev/fd/2
