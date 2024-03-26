#!/bin/bash

ORIGINAL_LOCATION="/usr/bin/cargo"
NEW_LOCATION="/usr/bin/cargo_original"

if [ -f "$NEW_LOCATION" ]; then
    rm "/builddir/clippy-output.txt"
    exit 0
fi

mv -v $ORIGINAL_LOCATION $NEW_LOCATION

sed "s|REPLACE_ME|$NEW_LOCATION|g" > $ORIGINAL_LOCATION << 'EOF'
#!/bin/bash

ORIGINAL_PARAMS=("$@")

# FIXME: "build" doesn't have to *always* be the first arg
if [[ $1 == "build" ]]; then
    set -x
    set -- "clippy" "${@:2}"
    REPLACE_ME "$@" --message-format=json >> /builddir/clippy-output.txt
fi

REPLACE_ME "${ORIGINAL_PARAMS[@]}"
EOF

chmod +x $ORIGINAL_LOCATION
