#!/bin/bash

# Copyright (C) 2012-2021 Red Hat, Inc.
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
test "main" = "${BRANCH}" || VER="${VER}.${BRANCH//-/_}"
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
URL:        https://github.com/csutils/%{name}
Source0:    https://github.com/csutils/%{name}/releases/download/%{name}-%{version}/%{name}-%{version}.tar.xz

BuildRequires: cmake
BuildRequires: help2man

%if 0%{?rhel} == 7
%global python3_pkgversion 36
%endif

BuildRequires: python%{python3_pkgversion}-GitPython
BuildRequires: python%{python3_pkgversion}-devel

Requires: csmock-common                 >= %{version}-%{release}
Requires: csmock-plugin-clang           >= %{version}-%{release}
Requires: csmock-plugin-cppcheck        >= %{version}-%{release}
Requires: csmock-plugin-shellcheck      >= %{version}-%{release}

BuildArch: noarch

%description
This is a metapackage pulling in csmock-common and basic csmock plug-ins.

%package -n csbuild
Summary: Tool for plugging static analyzers into the build process
Requires: cscppc
Requires: csclng
Requires: csdiff
Requires: csmock-common(python3)
Requires: cswrap
Requires: python%{python3_pkgversion}-GitPython

%description -n csbuild
Tool for plugging static analyzers into the build process, free of mock.

%package -n csmock-common
Summary: Core of csmock (a mock wrapper for Static Analysis tools)
Requires: csdiff
Requires: csgcca
Requires: cswrap
Requires: mock
Provides: csmock-common(python3) = %{version}-%{release}

%description -n csmock-common
This package contains the csmock tool that allows to scan SRPMs by Static
Analysis tools in a fully automated way.

%package -n csmock-plugin-bandit
Summary: csmock plug-in providing the support for Bandit.
Requires: csmock-common(python3)

%description -n csmock-plugin-bandit
This package contains the bandit plug-in for csmock.

%package -n csmock-plugin-cbmc
Summary: csmock plug-in providing the support for cbmc
Requires: cbmc-utils
Requires: csexec
Requires: csmock-common(python3)

%description -n csmock-plugin-cbmc
This package contains the cbmc plug-in for csmock.

%package -n csmock-plugin-clang
Summary: csmock plug-in providing the support for Clang
Requires: csclng
Requires: csmock-common(python3)

%description -n csmock-plugin-clang
This package contains the clang plug-in for csmock.

%package -n csmock-plugin-cppcheck
Summary: csmock plug-in providing the support for Cppcheck
Requires: cscppc
Requires: csmock-common(python3)

%description -n csmock-plugin-cppcheck
This package contains the cppcheck plug-in for csmock.

%package -n csmock-plugin-divine
Summary: csmock plug-in providing the support for divine
Requires: csexec
Requires: csmock-common(python3)

%description -n csmock-plugin-divine
This package contains the divine plug-in for csmock.

%package -n csmock-plugin-gitleaks
Summary: experimental csmock plug-in
Requires: csmock-common(python3)

%description -n csmock-plugin-gitleaks
This package contains the gitleaks plug-in for csmock.

%package -n csmock-plugin-infer
Summary: csmock plug-in providing the support for Infer
Requires: csmock-common(python3)

%description -n csmock-plugin-infer
This package contains the Infer plug-in for csmock.

%package -n csmock-plugin-pylint
Summary: csmock plug-in providing the support for Pylint.
Requires: csmock-common(python3)

%description -n csmock-plugin-pylint
This package contains the pylint plug-in for csmock.

%package -n csmock-plugin-shellcheck
Summary: csmock plug-in providing the support for ShellCheck.
Requires: csmock-common(python3)

%description -n csmock-plugin-shellcheck
This package contains the shellcheck plug-in for csmock.

%package -n csmock-plugin-smatch
Summary: csmock plug-in providing the support for smatch
Requires: csdiff
Requires: csmatch
Requires: csmock-common(python3)
Requires: cswrap

%description -n csmock-plugin-smatch
This package contains the smatch plug-in for csmock.

%package -n csmock-plugin-strace
Summary: csmock plug-in providing the support for strace
Requires: csexec
Requires: csmock-common(python3)

%description -n csmock-plugin-strace
This package contains the strace plug-in for csmock.

%package -n csmock-plugin-symbiotic
Summary: csmock plug-in providing the support for symbiotic
Requires: csexec
Requires: csmock-common(python3)

%description -n csmock-plugin-symbiotic
This package contains the symbiotic plug-in for csmock.

%package -n csmock-plugin-valgrind
Summary: csmock plug-in providing the support for valgrind
Requires: csexec
Requires: csmock-common(python3)

%description -n csmock-plugin-valgrind
This package contains the valgrind plug-in for csmock.

%package -n csmock-plugin-unicontrol
Summary: experimental csmock plug-in
Requires: csmock-common(python3)

%description -n csmock-plugin-unicontrol
This package contains the unicontrol plug-in for csmock.

%prep
%setup -q

# force using Python 3
sed -e '1s/python$/python3/' -i py/cs{build,mock}

%build
mkdir csmock_build
cd csmock_build
%cmake \\
    -DVERSION='%{name}-%{version}-%{release}' \\
    -DPYTHON_EXECUTABLE='%{__python3}' \\
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
%dir %{python3_sitelib}/csmock
%dir %{python3_sitelib}/csmock/plugins
%{_bindir}/csmock
%{_mandir}/man1/csmock.1*
%{_datadir}/csmock/cwe-map.csv
%{_datadir}/csmock/scripts/enable-keep-going.sh
%{_datadir}/csmock/scripts/chroot-fixups
%{_datadir}/csmock/scripts/patch-rawbuild.sh
%{python3_sitelib}/csmock/__init__.py*
%{python3_sitelib}/csmock/common
%{python3_sitelib}/csmock/plugins/__init__.py*
%{python3_sitelib}/csmock/plugins/gcc.py*
%{python3_sitelib}/csmock/__pycache__/__init__.*
%{python3_sitelib}/csmock/plugins/__pycache__/__init__.*
%{python3_sitelib}/csmock/plugins/__pycache__/gcc.*
%doc COPYING README

%files -n csmock-plugin-bandit
%{_datadir}/csmock/scripts/run-bandit.sh
%{python3_sitelib}/csmock/plugins/bandit.py*
%{python3_sitelib}/csmock/plugins/__pycache__/bandit.*

%files -n csmock-plugin-cbmc
%{python3_sitelib}/csmock/plugins/cbmc.py*
%{python3_sitelib}/csmock/plugins/__pycache__/cbmc.*

%files -n csmock-plugin-clang
%{python3_sitelib}/csmock/plugins/clang.py*
%{python3_sitelib}/csmock/plugins/__pycache__/clang.*

%files -n csmock-plugin-cppcheck
%{python3_sitelib}/csmock/plugins/cppcheck.py*
%{python3_sitelib}/csmock/plugins/__pycache__/cppcheck.*

%files -n csmock-plugin-divine
%{python3_sitelib}/csmock/plugins/divine.py*
%{python3_sitelib}/csmock/plugins/__pycache__/divine.*

%files -n csmock-plugin-gitleaks
%{_bindir}/gitleaks-convert-output
%{python3_sitelib}/csmock/plugins/gitleaks.py*
%{python3_sitelib}/csmock/plugins/__pycache__/gitleaks.*

%files -n csmock-plugin-infer
%{_datadir}/csmock/scripts/filter-infer.py
%{_datadir}/csmock/scripts/install-infer.sh
%{python3_sitelib}/csmock/plugins/infer.py*
%{python3_sitelib}/csmock/plugins/__pycache__/infer.*

%files -n csmock-plugin-pylint
%{_datadir}/csmock/scripts/run-pylint.sh
%{python3_sitelib}/csmock/plugins/pylint.py*
%{python3_sitelib}/csmock/plugins/__pycache__/pylint.*

%files -n csmock-plugin-shellcheck
%{_datadir}/csmock/scripts/run-shellcheck.sh
%{python3_sitelib}/csmock/plugins/shellcheck.py*
%{python3_sitelib}/csmock/plugins/__pycache__/shellcheck.*

%files -n csmock-plugin-smatch
%{python3_sitelib}/csmock/plugins/smatch.py*
%{python3_sitelib}/csmock/plugins/__pycache__/smatch.*

%files -n csmock-plugin-strace
%{python3_sitelib}/csmock/plugins/strace.py*
%{python3_sitelib}/csmock/plugins/__pycache__/strace.*

%files -n csmock-plugin-symbiotic
%{python3_sitelib}/csmock/plugins/symbiotic.py*
%{python3_sitelib}/csmock/plugins/__pycache__/symbiotic.*

%files -n csmock-plugin-valgrind
%{python3_sitelib}/csmock/plugins/valgrind.py*
%{python3_sitelib}/csmock/plugins/__pycache__/valgrind.*

%files -n csmock-plugin-unicontrol
%{_datadir}/csmock/scripts/find-unicode-control.py*
%{python3_sitelib}/csmock/plugins/unicontrol.py*
%{python3_sitelib}/csmock/plugins/__pycache__/unicontrol.*
EOF

rpmbuild -bs "$SPEC"                            \
    --define "_sourcedir $TMP"                  \
    --define "_specdir $TMP"                    \
    --define "_srcrpmdir $DST"
