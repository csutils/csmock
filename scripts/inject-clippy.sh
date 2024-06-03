#!/bin/bash

ORIGINAL_LOCATION="/usr/bin/cargo"
NEW_LOCATION="/usr/bin/cargo_original"

if [ -f "$NEW_LOCATION" ]; then
    # remove capture file created by previous runs if --skip-init is in effect
    rm -fv "/builddir/clippy-output.txt"
    exit 0
fi

mv -v $ORIGINAL_LOCATION $NEW_LOCATION

sed "s|REPLACE_ME|$NEW_LOCATION|g" > $ORIGINAL_LOCATION << 'EOF'
#!/bin/bash

# look for "build" in command-line args
for ((i=1; i<$#; i++)); do
    if [[ "${!i}" == "build" ]]; then
        # found! --> execute the command with "build" substituted by "clippy"
        set -x
        REPLACE_ME "${@:1:i-1}" clippy "${@:i+1}" --message-format=json >> /builddir/clippy-output.txt
        break
    fi
done

# execute the original command in any case
exec REPLACE_ME "$@"
EOF

chmod +x $ORIGINAL_LOCATION
