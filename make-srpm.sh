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

die() {
    echo "$SELF: error: $1" >&2
    exit 1
}

match() {
    grep "$@" > /dev/null
}

DST="`readlink -f "$PWD"`"

REPO="`git rev-parse --show-toplevel`"
test -d "$REPO" || die "not in a git repo"

NV="`git describe --tags`"
echo "$NV" | match "^$PKG-" || die "release tag not found"

VER="`echo "$NV" | sed "s/^$PKG-//"`"

TIMESTAMP="`git log --pretty="%cd" --date=iso -1 \
    | tr -d ':-' | tr ' ' . | cut -d. -f 1,2`"

VER="`echo "$VER" | sed "s/-.*-/.$TIMESTAMP./"`"

BRANCH="`git rev-parse --abbrev-ref HEAD`"
test -n "$BRANCH" || die "failed to get current branch name"
test master = "${BRANCH}" || VER="${VER}.${BRANCH}"
test -z "`git diff HEAD`" || VER="${VER}.dirty"

NV="${PKG}-${VER}"
printf "%s: preparing a release of \033[1;32m%s\033[0m\n" "$SELF" "$NV"

TMP="`mktemp -d`"
trap "echo --- $SELF: removing $TMP... 2>&1; rm -rf '$TMP'" EXIT
test -d "$TMP" || die "mktemp failed"

SRC_TAR="${NV}.tar"
SRC="${SRC_TAR}.xz"
git archive --prefix="$NV/" --format="tar" HEAD -- . > "${TMP}/${SRC_TAR}" \
                                        || die "failed to export sources"
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
URL:        https://git.fedorahosted.org/cgit/csmock.git
Source0:    https://git.fedorahosted.org/cgit/csmock.git/snapshot/$SRC
BuildRoot:  %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: help2man
BuildRequires: python-devel
%if !(0%{?fedora} >= 19 || 0%{?rhel} >= 7)
BuildRequires: python-argparse
%endif

Requires: csdiff
Requires: cswrap
Requires: mock
Requires: rpm-build

# TODO: make these sub-packages optional
Requires: csmock-plugin-clang
Requires: csmock-plugin-cppcheck

Obsoletes: csmock-ng <= 1.1.1

BuildArch: noarch

%description
This package contains cov-mockbuild and cov-diffbuild tools that allow to scan
SRPMs by Static Analysis tools in a fully automated way.

%package -n csmock-plugin-clang
Summary: csmock plug-in providing the support for Clang
Requires: csmock

%description -n csmock-plugin-clang
Hihgly experimental, currently suitable only for development of csmock itself.

%package -n csmock-plugin-cppcheck
Summary: csmock plug-in providing the support for Cppcheck
Requires: cscppc
Requires: csmock

%description -n csmock-plugin-cppcheck
Hihgly experimental, currently suitable only for development of csmock itself.

%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

%prep
%setup -q

%build
mkdir -p bin man

# embed VERSION and PLUGIN_DIR version into the scripts
install -p -m0755 cov-{diff,mock}build bin/
sed -e 's/rpm -qf .SELF/echo %{version}/' -i bin/cov-{diff,mock}build
sed -e 's/@VERSION@/%{name}-%{version}-%{release}/' \\
    -e 's|@PLUGIN_DIR@|%{python2_sitelib}/csmock/plugins|' \\
    -i py/csmock

help2man --no-info --section 1 --name \\
    "run static analysis of the given SRPM using mock" \\
    bin/cov-mockbuild > man/cov-mockbuild.1

help2man --no-info --section 1 --name \\
    "run static analysis of the given the patches in the given SRPM using cov-mockbuild" \\
    bin/cov-diffbuild > man/cov-diffbuild.1

help2man --no-info --section 1 --name \\
    "run static analysis of the given SRPM using mock" \\
    py/csmock > man/csmock.1

%clean
rm -rf "\$RPM_BUILD_ROOT"

%install
rm -rf "\$RPM_BUILD_ROOT"

install -m0755 -d \\
    "\$RPM_BUILD_ROOT%{_bindir}" \\
    "\$RPM_BUILD_ROOT%{_mandir}/man1" \\
    "\$RPM_BUILD_ROOT%{_datadir}/csmock" \\
    "\$RPM_BUILD_ROOT%{_datadir}/csmock/scripts" \\
    "\$RPM_BUILD_ROOT%{python2_sitelib}/" \\
    "\$RPM_BUILD_ROOT%{python2_sitelib}/csmock" \\
    "\$RPM_BUILD_ROOT%{python2_sitelib}/csmock/plugins"

install -p -m0755 \\
    cov-{diff,mock}build cov-dump-err rpmbuild-rawbuild py/csmock \\
    "\$RPM_BUILD_ROOT%{_bindir}"

install -p -m0644 man/{csmock,cov-{diff,mock}build}.1 "\$RPM_BUILD_ROOT%{_mandir}/man1/"

install -p -m0644 cov_checker_map.txt "\$RPM_BUILD_ROOT%{_datadir}/csmock/cwe-map.csv"

install -p -m0644 py/plugins/*.py \\
    "\$RPM_BUILD_ROOT%{python2_sitelib}/csmock/plugins"

install -p -m0755 scripts/*.sh \\
    "\$RPM_BUILD_ROOT%{_datadir}/csmock/scripts"

%files
%defattr(-,root,root,-)
%{_bindir}/cov-dump-err
%{_bindir}/cov-diffbuild
%{_bindir}/cov-mockbuild
%{_bindir}/csmock
%{_bindir}/rpmbuild-rawbuild
%{_mandir}/man1/cov-diffbuild.1*
%{_mandir}/man1/cov-mockbuild.1*
%{_mandir}/man1/csmock.1*
%{_datadir}/csmock/cwe-map.csv
%{_datadir}/csmock/scripts/patch-rawbuild.sh
%{python2_sitelib}/csmock/plugins/gcc.py*
%doc COPYING

%files -n csmock-plugin-clang
%defattr(-,root,root,-)
%{_datadir}/csmock/scripts/fixups-clang.sh
%{python2_sitelib}/csmock/plugins/clang.py*

%files -n csmock-plugin-cppcheck
%defattr(-,root,root,-)
%{python2_sitelib}/csmock/plugins/cppcheck.py*
EOF

rpmbuild -bs "$SPEC"                            \
    --define "_sourcedir $TMP"                  \
    --define "_specdir $TMP"                    \
    --define "_srcrpmdir $DST"                  \
    --define "_source_filedigest_algorithm md5" \
    --define "_binary_filedigest_algorithm md5"
