#!/bin/bash

ORIGINAL_BINARY="/usr/bin/cargo"
NEW_LOCATION="/usr/bin/cargo_original"

mv $ORIGINAL_BINARY $NEW_LOCATION

cat > $ORIGINAL_BINARY << 'EOF'
#!/bin/bash

ORIGINAL_PARAMS=("$@")

if [[ $1 == "build" ]]; then
    set -- "clippy" "${@:2}"
    REPLACE_ME "$@" --message-format=json >> /builddir/clippy-output.txt
fi

REPLACE_ME "${ORIGINAL_PARAMS[@]}"
EOF

sed -i "s|REPLACE_ME|$NEW_LOCATION|g" $ORIGINAL_BINARY

chmod +x $ORIGINAL_BINARY
