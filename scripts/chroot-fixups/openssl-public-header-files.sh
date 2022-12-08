#!/bin/sh

if test -w /usr/include/openssl/e_os2.h; then
    (set -x

    # behave as if the code was preprocessed with -DDEBUG_UNUSED
    sed -i /usr/include/openssl/e_os2.h \
        -e 's|\(# *if\)def DEBUG_UNUSED|\1 1|')
fi
