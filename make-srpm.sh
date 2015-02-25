#/bin/bash

# Copyright (C) 2012-2015 Red Hat, Inc.
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

BuildRequires: GitPython
BuildRequires: cmake
BuildRequires: help2man
BuildRequires: python-devel
%if !(0%{?fedora} >= 19 || 0%{?rhel} >= 7)
BuildRequires: python-argparse
%endif

Requires: csmock-common
Requires: csmock-plugin-clang
Requires: csmock-plugin-cppcheck
Requires: csmock-plugin-pylint
Requires: csmock-plugin-shellcheck

BuildArch: noarch

%description
This is a metapackage pulling in csmock-common and basic csmock plug-ins.

%package -n csbuild
Summary: Tool for plugging static analyzers into the build process
Requires: GitPython
Requires: cscppc
Requires: csclng
Requires: csdiff >= 1.1.2
Requires: cswrap

%description -n csbuild
Tool for plugging static analyzers into the build process, free of mock.

%package -n csmock-common
Summary: Core of csmock (a mock wrapper for Static Analysis tools)
Requires: csdiff
Requires: cswrap
Requires: mock

%description -n csmock-common
This package contains the csmock tool that allows to scan SRPMs by Static
Analysis tools in a fully automated way.

%package -n csmock-plugin-clang
Summary: csmock plug-in providing the support for Clang
Requires: csclng
Requires: csmock-common > 1.7.0

%description -n csmock-plugin-clang
This package contains the clang plug-in for csmock.

%package -n csmock-plugin-cppcheck
Summary: csmock plug-in providing the support for Cppcheck
Requires: cscppc >= 1.0.4
Requires: csmock-common

%description -n csmock-plugin-cppcheck
This package contains the cppcheck plug-in for csmock.

%package -n csmock-plugin-pylint
Summary: csmock plug-in providing the support for Pylint.
Requires: csmock-common > 1.7.0

%description -n csmock-plugin-pylint
This package contains the pylint plug-in for csmock.

%package -n csmock-plugin-shellcheck
Summary: csmock plug-in providing the support for ShellCheck.
Requires: csmock-common > 1.7.0

%description -n csmock-plugin-shellcheck
This package contains the shellcheck plug-in for csmock.

%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

%prep
%setup -q

%build
mkdir csmock_build
cd csmock_build
%cmake '-DVERSION=%{name}-%{version}-%{release}' ..
make %{?_smp_mflags} VERBOSE=yes

%install
cd csmock_build
make install DESTDIR="\$RPM_BUILD_ROOT"

# needed to create the csmock RPM
%files

%files -n csbuild
%{_bindir}/csbuild
%{_mandir}/man1/csbuild.1*
%{_datadir}/csbuild/scripts/run-scan.sh
%doc COPYING

%files -n csmock-common
%{_bindir}/csmock
%{_mandir}/man1/csmock.1*
%{_datadir}/csmock/cwe-map.csv
%{_datadir}/csmock/scripts/patch-rawbuild.sh
%{python2_sitelib}/csmock/__init__.py*
%{python2_sitelib}/csmock/common/__init__.py*
%{python2_sitelib}/csmock/common/util.py*
%{python2_sitelib}/csmock/plugins/gcc.py*
%doc COPYING README

%files -n csmock-plugin-clang
%{python2_sitelib}/csmock/plugins/clang.py*

%files -n csmock-plugin-cppcheck
%{python2_sitelib}/csmock/plugins/cppcheck.py*

%files -n csmock-plugin-pylint
%{_datadir}/csmock/scripts/run-pylint.sh
%{python2_sitelib}/csmock/plugins/pylint.py*

%files -n csmock-plugin-shellcheck
%{_datadir}/csmock/scripts/run-shellcheck.sh
%{python2_sitelib}/csmock/plugins/shellcheck.py*
EOF

rpmbuild -bs "$SPEC"                            \
    --define "_sourcedir $TMP"                  \
    --define "_specdir $TMP"                    \
    --define "_srcrpmdir $DST"
