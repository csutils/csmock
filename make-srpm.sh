#/bin/bash
SELF="$0"

PKG="cov-mockbuild"

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

VER="0.`git log --pretty="%cd_%h" --date=short -1 | tr -d -`" \
    || die "git log failed"

NV="${PKG}-$VER"
SRC="${PKG}.tar.xz"

TMP="`mktemp -d`"
trap "echo --- $SELF: removing $TMP... 2>&1; rm -rf '$TMP'" EXIT
test -d "$TMP" || die "mktemp failed"
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
Source2:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=aux/rpmbuild-rawbuild
Source3:    http://git.engineering.redhat.com/?p=users/kdudka/coverity-scan.git;a=blob_plain;f=mock/bashrc

Requires: cov-sa
Requires: csdiff
Requires: mock
Requires: rpm-build

BuildArch:  noarch
Obsoletes:  cov-mockbuild.x86_64 < %{version}-%{release}

%description
This package contains cov-mockbuild and cov-diffbuild tools that allow to scan
SRPMs by Coverity Static Analysis in a fully automated way.

%install
install -m0755 -d "\$RPM_BUILD_ROOT%{_bindir}" "\$RPM_BUILD_ROOT/usr/share/covscan"
install -m0755 %{SOURCE0} %{SOURCE1} %{SOURCE2} "\$RPM_BUILD_ROOT%{_bindir}"
install -m0644 %{SOURCE3} "\$RPM_BUILD_ROOT/usr/share/covscan"

%files
%defattr(-,root,root,-)
%{_bindir}/cov-diffbuild
%{_bindir}/cov-mockbuild
%{_bindir}/rpmbuild-rawbuild
/usr/share/covscan
EOF

rpmbuild -bs "$SPEC"            \
    --define "_sourcedir ."     \
    --define "_specdir ."       \
    --define "_srcrpmdir $DST"
