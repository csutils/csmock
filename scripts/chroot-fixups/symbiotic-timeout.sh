#!/bin/bash

for file in /opt/symbiotic/lib/symbioticpy/symbiotic/{transform,verifier}.py; do
    [ -w ${file} ] || continue

    # Make sure that symbiotic uses the system-provided timeout(1) for itself.
    # Otherwise, when formally verifying the coreutils RPM package by Symbiotic,
    # the test-suite puts our instrumented binary of timeout(1) into ${PATH},
    # causing it to recursively invoke whole symbiotic on each invocation of
    # timeout within symbiotic.
    (
        set -x
        sed -e "s|'timeout'|'/usr/bin/timeout'|" -i ${file}
    )
done
