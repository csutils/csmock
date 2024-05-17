#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

CSMOCK_EXTRA_OPTS="${CSMOCK_EXTRA_OPTS:-}"
TEST_PACKAGE="${TEST_PACKAGE:-}"
TEST_TOOL="${TEST_TOOL:-}"
TEST_USER="csmock"

rlJournalStart
    rlPhaseStartSetup
        # use the latest csutils in the Testing Farm
        if rlIsFedora || rlIsRHELLike '>7'; then
            # By default the testing-farm-tag-repository has higher priority
            # than our development COPR repo.  Therefore, we need to flip the
            # priorities and update the packages manually.
            rlRun "echo 'priority=1' >> /etc/yum.repos.d/group_codescan-csutils-*.repo"
            rlRun "dnf upgrade -y 'cs*'"
        fi

        if [ -z "$TEST_PACKAGE" ]; then
            rlDie "TEST_PACKAGE parameter is empty or undefined"
        fi

        if [ -z "$TEST_TOOL" ]; then
            rlDie "TEST_TOOL parameter is empty or undefined"
        fi

        # create a tmpdir
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd \$tmp"

        # fetch the SRPM
        rlRun "yum -y install $TEST_PACKAGE"
        rlRun "rlFetchSrcForInstalled $TEST_PACKAGE"
        rlRun "SRPM=\$(find . -name '$TEST_PACKAGE-*.src.rpm')"

        # add a user for mock
        rlRun "userdel -r $TEST_USER" 0,6
        rlRun "useradd -m -d /home/$TEST_USER -G mock $TEST_USER"
        rlRun "cp $SRPM /home/$TEST_USER"

        if ! rlGetPhaseState; then
            rlDie "'$TEST_PACKAGE' sources could not be fetched"
        fi
    rlPhaseEnd

    rlPhaseStartTest "Analyze $TEST_PACKAGE using $TEST_TOOL"
        rlRun "su - $TEST_USER -c 'csmock -t $TEST_TOOL $CSMOCK_EXTRA_OPTS \"$SRPM\"'" 0 \
            "Analyze $SRPM using $TEST_TOOL analyzer"
        rlFileSubmit "/home/$TEST_USER/$TEST_PACKAGE"*.tar.xz "$SRPM-$TEST_TOOL.tar.xz"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "userdel -r $TEST_USER"
        rlRun "popd"
        rlRun "rm -r \$tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
