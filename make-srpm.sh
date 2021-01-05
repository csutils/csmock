#/bin/bash

# Copyright (C) 2012-2018 Red Hat, Inc.
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
test master = "${BRANCH}" || VER="${VER}.${BRANCH//-/_}"
test -z "`git diff HEAD`" || VER="${VER}.dirty"

NV="${PKG}-${VER}"
printf "%s: preparing a release of \033[1;32m%s\033[0m\n" "$SELF" "$NV"

TMP="`mktemp -d`"
trap "rm -rf '$TMP'" EXIT
cd "$TMP" >/dev/null || die "mktemp failed"

# clone the repository
git clone "$REPO" "$PKG"                || die "git clone failed"
cd "$PKG"                               || die "git clone failed"

make -j5 distcheck CTEST='ctest -j5'    || die "'make distcheck' has failed"

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

License:    GPLv3+
URL:        https://github.com/kdudka/%{name}
Source0:    https://github.com/kdudka/%{name}/releases/download/%{name}-%{version}/%{name}-%{version}.tar.xz

BuildRequires: cmake
BuildRequires: help2man

%if !(0%{?fedora} >= 19 || 0%{?rhel} >= 7)
BuildRequires: python-argparse
BuildRequires: python-importlib
%endif

# force using Python 3 Fedora 23+
%global force_py3 ((7 < 0%{?rhel}) || (22 < 0%{?fedora}))
%if %{force_py3}
BuildRequires: python3-GitPython
BuildRequires: python3-devel
%global csmock_python_executable %{__python3}
%global csmock_python_sitelib %{python3_sitelib}
%else
BuildRequires: GitPython
BuildRequires: python2-devel
%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif
%global csmock_python_executable %{__python2}
%global csmock_python_sitelib %{python2_sitelib}
%endif

Requires: csmock-common                 >= %{version}-%{release}
Requires: csmock-plugin-clang           >= %{version}-%{release}
Requires: csmock-plugin-cppcheck        >= %{version}-%{release}
Requires: csmock-plugin-shellcheck      >= %{version}-%{release}

BuildArch: noarch

%description
This is a metapackage pulling in csmock-common and basic csmock plug-ins.

%package -n csbuild
Summary: Tool for plugging static analyzers into the build process
%if %{force_py3}
Requires: csmock-common(python3)
Requires: python3-GitPython
%else
Requires: GitPython
%endif
Requires: cscppc
Requires: csclng
Requires: csdiff >= 1.5.0
Requires: cswrap
Requires: csmock-common > 2.1.1

%description -n csbuild
Tool for plugging static analyzers into the build process, free of mock.

%package -n csmock-common
Summary: Core of csmock (a mock wrapper for Static Analysis tools)
Requires: csdiff > 1.8.0
Requires: csgcca
Requires: cswrap >= 1.3.1
Requires: mock
%if !(0%{?fedora} >= 19 || 0%{?rhel} >= 7)
Requires: python-argparse
Requires: python-importlib
%endif
%if %{force_py3}
Provides: csmock-common(python3) = %{version}-%{release}
%endif

%description -n csmock-common
This package contains the csmock tool that allows to scan SRPMs by Static
Analysis tools in a fully automated way.

%package -n csmock-plugin-bandit
Summary: csmock plug-in providing the support for Bandit.
Requires: csmock-common >= 1.8.0
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-bandit
This package contains the bandit plug-in for csmock.

%package -n csmock-plugin-clang
Summary: csmock plug-in providing the support for Clang
Requires: csclng
Requires: csmock-common >= 1.7.1
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-clang
This package contains the clang plug-in for csmock.

%package -n csmock-plugin-cppcheck
Summary: csmock plug-in providing the support for Cppcheck
Requires: cscppc >= 1.0.4
Requires: csmock-common
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-cppcheck
This package contains the cppcheck plug-in for csmock.

%package -n csmock-plugin-pylint
Summary: csmock plug-in providing the support for Pylint.
Requires: csmock-common >= 1.8.0
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-pylint
This package contains the pylint plug-in for csmock.

%package -n csmock-plugin-shellcheck
Summary: csmock plug-in providing the support for ShellCheck.
Requires: csmock-common >= 1.8.0
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-shellcheck
This package contains the shellcheck plug-in for csmock.

%package -n csmock-plugin-smatch
Summary: csmock plug-in providing the support for smatch
Requires: csdiff > 1.4.0
Requires: csmatch
Requires: csmock-common
Requires: cswrap > 1.4.0
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-smatch
This package contains the smatch plug-in for csmock.

%package -n csmock-plugin-strace
Summary: csmock plug-in providing the support for strace
Requires: csexec
Requires: csmock-common > 2.6.0
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-strace
This package contains the strace plug-in for csmock.

%package -n csmock-plugin-valgrind
Summary: csmock plug-in providing the support for valgrind
Requires: csexec
Requires: csmock-common > 2.6.0
%if %{force_py3}
Requires: csmock-common(python3)
%endif

%description -n csmock-plugin-valgrind
This package contains the valgrind plug-in for csmock.

%prep
%setup -q

# force using Python 3 Fedora 23+
%if %{force_py3}
sed -e '1s/python$/python3/' -i py/cs{build,mock}
%endif

%build
mkdir csmock_build
cd csmock_build
%cmake \\
    -DVERSION='%{name}-%{version}-%{release}' \\
    -DPYTHON_EXECUTABLE='%{csmock_python_executable}' \\
    -B. ..
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
%dir %{_datadir}/csmock
%dir %{_datadir}/csmock/scripts
%dir %{csmock_python_sitelib}/csmock
%dir %{csmock_python_sitelib}/csmock/plugins
%{_bindir}/csmock
%{_mandir}/man1/csmock.1*
%{_datadir}/csmock/cwe-map.csv
%{_datadir}/csmock/scripts/chroot-fixups
%{_datadir}/csmock/scripts/patch-rawbuild.sh
%{csmock_python_sitelib}/csmock/__init__.py*
%{csmock_python_sitelib}/csmock/common
%{csmock_python_sitelib}/csmock/plugins/__init__.py*
%{csmock_python_sitelib}/csmock/plugins/gcc.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/__pycache__/__init__.*
%{csmock_python_sitelib}/csmock/plugins/__pycache__/__init__.*
%{csmock_python_sitelib}/csmock/plugins/__pycache__/gcc.*
%endif
%doc COPYING README

%files -n csmock-plugin-bandit
%{_datadir}/csmock/scripts/run-bandit.sh
%{csmock_python_sitelib}/csmock/plugins/bandit.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/bandit.*
%endif

%files -n csmock-plugin-clang
%{csmock_python_sitelib}/csmock/plugins/clang.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/clang.*
%endif

%files -n csmock-plugin-cppcheck
%{csmock_python_sitelib}/csmock/plugins/cppcheck.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/cppcheck.*
%endif

%files -n csmock-plugin-pylint
%{_datadir}/csmock/scripts/run-pylint.sh
%{csmock_python_sitelib}/csmock/plugins/pylint.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/pylint.*
%endif

%files -n csmock-plugin-shellcheck
%{_datadir}/csmock/scripts/run-shellcheck.sh
%{csmock_python_sitelib}/csmock/plugins/shellcheck.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/shellcheck.*
%endif

%files -n csmock-plugin-smatch
%{csmock_python_sitelib}/csmock/plugins/smatch.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/smatch.*
%endif

%files -n csmock-plugin-strace
%{csmock_python_sitelib}/csmock/plugins/strace.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/strace.*
%endif

%files -n csmock-plugin-valgrind
%{csmock_python_sitelib}/csmock/plugins/valgrind.py*
%if %{force_py3}
%{csmock_python_sitelib}/csmock/plugins/__pycache__/valgrind.*
%endif
EOF

rpmbuild -bs "$SPEC"                            \
    --define "_sourcedir $TMP"                  \
    --define "_specdir $TMP"                    \
    --define "_srcrpmdir $DST"
