#/bin/bash
SELF="$0"

PKG="csmock"

die(){
    echo "$SELF: error: $1" >&2
    exit 1
}

DST="`readlink -f "$PWD"`"

REPO="`git rev-parse --show-toplevel`" \
    || die "not in a git repo"

printf "%s: considering release of %s using %s...\n" \
    "$SELF" "$PKG" "$REPO"

branch="`git status | head -1 | sed 's/^#.* //'`" \
    || die "unable to read git branch"

test xmaster = "x$branch" \
    || die "not in master branch"

test -z "`git diff HEAD`" \
    || die "HEAD dirty"

test -z "`git diff origin/master`" \
    || die "not synced with origin/master"

VER="0.`git log --pretty="%cd_%h" --date=short -1 . | tr -d -`" \
    || die "git log failed"

NV="${PKG}-$VER"
SRC="${PKG}.tar.xz"

TMP="`mktemp -d`"
trap "echo --- $SELF: removing $TMP... 2>&1; rm -rf '$TMP'" EXIT
test -d "$TMP" || die "mktemp failed"
cp -t "$TMP"                        \
    ./*.bashrc                      \
    ./cov_checker_map.txt           \
    ./cov-dump-err                  \
    ./cov-{mock,diff}build          \
    ./rpmbuild-rawbuild

SPEC="$TMP/$PKG.spec"
cat > "$SPEC" << EOF
Name:       $PKG
Version:    $VER
Release:    1%{?dist}
Summary:    A mock wrapper for Coverity Static Analysis tools

Group:      CoverityScan
License:    GPLv3+
URL:        https://engineering.redhat.com/trac/CoverityScan
Source0:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/cov-mockbuild
Source1:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/cov-diffbuild
Source2:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/cov-dump-err
Source3:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/rpmbuild-rawbuild
Source4:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/build.bashrc
Source5:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/prep.bashrc
Source6:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/cov_checker_map.txt

BuildRoot:  %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: help2man

Requires: cscppc
Requires: csdiff
Requires: cswrap
Requires: mock
Requires: rpm-build

BuildArch: noarch


%description
This package contains cov-mockbuild and cov-diffbuild tools that allow to scan
SRPMs by Coverity Static Analysis in a fully automated way.

%build
mkdir -p bin etc man sbin

install -m0755 %{SOURCE0} %{SOURCE1} bin/
sed -e 's/rpm -qf .SELF/echo %{version}/' -i bin/cov-{diff,mock}build

help2man --no-info --section 1 --name \\
    "run static analysis of the given SRPM using mock" \\
    bin/cov-mockbuild | gzip -c > man/cov-mockbuild.1.gz

help2man --no-info --section 1 --name \\
    "run static analysis of the given the patches in the given SRPM using cov-mockbuild" \\
    bin/cov-diffbuild | gzip -c > man/cov-diffbuild.1.gz

printf '#!/bin/sh\\nstdbuf -o0 /usr/sbin/mock "\$@"\\n' > ./sbin/mock-unbuffered
printf 'USER=root\\nPROGRAM=/usr/sbin/mock-unbuffered\\nSESSION=false
FALLBACK=false\\nKEEP_ENV_VARS=COLUMNS,SSH_AUTH_SOCK\\n' > ./etc/mock-unbuffered

%clean
rm -rf "\$RPM_BUILD_ROOT"

%install
rm -rf "\$RPM_BUILD_ROOT"

install -m0755 -d \\
    "\$RPM_BUILD_ROOT%{_bindir}" \\
    "\$RPM_BUILD_ROOT%{_mandir}/man1" \\
    "\$RPM_BUILD_ROOT%{_sbindir}" \\
    "\$RPM_BUILD_ROOT%{_datadir}/covscan" \\
    "\$RPM_BUILD_ROOT%{_datadir}/covscan/bashrc"

install -m0755 \\
    %{SOURCE0} %{SOURCE1} %{SOURCE2} %{SOURCE3} \\
    "\$RPM_BUILD_ROOT%{_bindir}"

install -m0644 man/cov-{diff,mock}build.1.gz "\$RPM_BUILD_ROOT%{_mandir}/man1/"

install -m0644 %{SOURCE4} "\$RPM_BUILD_ROOT%{_datadir}/covscan/bashrc/build"
install -m0644 %{SOURCE5} "\$RPM_BUILD_ROOT%{_datadir}/covscan/bashrc/prep"
install -m0644 %{SOURCE6} "\$RPM_BUILD_ROOT%{_datadir}/covscan/cwe-map.csv"

install -m0755 -d \\
    "\$RPM_BUILD_ROOT%{_sysconfdir}/security/console.apps/" \\
    "\$RPM_BUILD_ROOT%{_sysconfdir}/pam.d/"

install -m0755 sbin/mock-unbuffered "\$RPM_BUILD_ROOT%{_sbindir}"

install -m0644 etc/mock-unbuffered \\
    "\$RPM_BUILD_ROOT%{_sysconfdir}/security/console.apps/"

ln -s mock "\$RPM_BUILD_ROOT%{_sysconfdir}/pam.d/mock-unbuffered"
ln -s consolehelper "\$RPM_BUILD_ROOT%{_bindir}/mock-unbuffered"

%files
%defattr(-,root,root,-)
%{_bindir}/cov-dump-err
%{_bindir}/cov-diffbuild
%{_bindir}/cov-mockbuild
%{_bindir}/rpmbuild-rawbuild
%{_mandir}/man1/cov-diffbuild.1.gz
%{_mandir}/man1/cov-mockbuild.1.gz
%{_datadir}/covscan

%{_bindir}/mock-unbuffered
%{_sbindir}/mock-unbuffered
%{_sysconfdir}/pam.d/mock-unbuffered
%config(noreplace) %{_sysconfdir}/security/console.apps/mock-unbuffered
EOF

rpmbuild -bs "$SPEC"                            \
    --define "_sourcedir $TMP"                  \
    --define "_specdir $TMP"                    \
    --define "_srcrpmdir $DST"                  \
    --define "_source_filedigest_algorithm md5" \
    --define "_binary_filedigest_algorithm md5"
