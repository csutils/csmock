#!/bin/sh

need_for_build() {
    while test -n "$1"; do
        if test "--suffix" = "$1"; then
            shift
            if test "_RAWBUILD" = "$1"; then
                return 0
            fi
        fi

        shift
    done

    return 1
}

if need_for_build "$@"; then
    echo "$0: applying a patch annotated by _RAWBUILD" >&2
    /usr/bin/patch "$@"
else
    echo "$0: ignoring a patch not annotated by _RAWBUILD" >&2
    dd of=/dev/null status=noxfer 2>/dev/null
fi
