#!/bin/sh

if [ -x /usr/lib64/libQt5Core.so.5 ]; then
    (set -x; strip --remove-section=.note.ABI-tag /usr/lib64/libQt5Core.so.5)
fi
