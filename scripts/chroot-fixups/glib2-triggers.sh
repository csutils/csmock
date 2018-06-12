#!/bin/sh

if [ -x /usr/bin/gio-querymodules-64 ] && [ -d /usr/lib64/gio/modules ]; then
    (set -x; /usr/bin/gio-querymodules-64 /usr/lib64/gio/modules)
fi

if [ -x /usr/bin/glib-compile-schemas ] && [ -d /usr/share/glib-2.0/schemas ]; then
    (set -x; /usr/bin/glib-compile-schemas /usr/share/glib-2.0/schemas)
fi
