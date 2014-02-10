#/bin/bash

# Copyright (C) 2012-2014 Red Hat, Inc.
#
# This file is part of csmock.
#
# csmock is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# csmock is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with csmock.  If not, see <http://www.gnu.org/licenses/>.

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

TMP="`mktemp -d`"
trap "echo --- $SELF: removing $TMP... 2>&1; rm -rf '$TMP'" EXIT
test -d "$TMP" || die "mktemp failed"

SRC_TAR="${PKG}.tar"
SRC="${SRC_TAR}.xz"
git archive --prefix="$NV/" --format="tar" HEAD -- . > "${TMP}/${SRC_TAR}"
cd "$TMP" >/dev/null                    || die "mktemp failed"
xz -c "$SRC_TAR" > "$SRC"               || die "failed to compress sources"

SPEC="$TMP/$PKG.spec"
cat > "$SPEC" << EOF
Name:       $PKG
Version:    $VER
Release:    1%{?dist}
Summary:    A mock wrapper for Static Analysis tools

Group:      Development/Tools
License:    GPLv3+
URL:        http://git.fedorahosted.org/cgit/csmock.git
Source0:    $SRC
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
SRPMs by Static Analysis tools in a fully automated way.

%prep
%setup -q

%build
mkdir -p bin etc man sbin

install -m0755 cov-{diff,mock}build bin/
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
    cov-{diff,mock}build cov-dump-err rpmbuild-rawbuild \\
    "\$RPM_BUILD_ROOT%{_bindir}"

install -m0644 man/cov-{diff,mock}build.1.gz "\$RPM_BUILD_ROOT%{_mandir}/man1/"

install -m0644 build.bashrc        "\$RPM_BUILD_ROOT%{_datadir}/covscan/bashrc/build"
install -m0644 prep.bashrc         "\$RPM_BUILD_ROOT%{_datadir}/covscan/bashrc/prep"
install -m0644 cov_checker_map.txt "\$RPM_BUILD_ROOT%{_datadir}/covscan/cwe-map.csv"

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

%doc COPYING
EOF

rpmbuild -bs "$SPEC"                            \
    --define "_sourcedir $TMP"                  \
    --define "_specdir $TMP"                    \
    --define "_srcrpmdir $DST"                  \
    --define "_source_filedigest_algorithm md5" \
    --define "_binary_filedigest_algorithm md5"
