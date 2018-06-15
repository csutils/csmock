#!/bin/sh

if [ -x /usr/bin/gdk-pixbuf-query-loaders-64 ]; then
    (set -x; /usr/bin/gdk-pixbuf-query-loaders-64 --update-cache)
fi
