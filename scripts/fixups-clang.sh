#!/bin/sh

if test -d /usr/lib64/clang-analyzer && ! test -d /usr/libexec/clang-analyzer
then
    # the directory was moved from %{_libdir} to %{_libexecdir}
    ln -sv ../lib64/clang-analyzer /usr/libexec/clang-analyzer
fi

if test -x /usr/libexec/clang-analyzer/scan-build/scan-build; then
    # allow scan-build to invoke clang through the cswrap wrapper
    patch /usr/libexec/clang-analyzer/scan-build/scan-build << EOF
1533,1534c1533
<       DieDiag("error: Cannot find an executable 'clang' relative to scan-build." .
<    	          "  Consider using --use-analyzer to pick a version of 'clang' to use for static analysis.\\n");
---
>       \$Clang = "clang";
EOF
fi

if test -x /usr/libexec/clang-analyzer/scan-build/ccc-analyzer; then
    # avoid failing with "could not find clang line" on mozjs17-17.0.0-9.el7
    # and glusterfs-3.6.0.15-1.el6
    sed -e "s/\$ENV{'CLANG'}/'clang'/" \
        -e "s/\$ENV{'CLANG_CXX'}/'clang++'/" \
        -i /usr/libexec/clang-analyzer/scan-build/ccc-analyzer

    if test -w /usr/bin/libtool; then
      # avoid failing on "unable to infer tagged configuration"
      sed -e 's/^available_tags=".*"$/available_tags=/' \
          -i /usr/bin/libtool
    fi
fi

if readlink /usr/libexec/clang-analyzer/scan-build/clang; then
    # prevent the symlink to shadow the cswrap symlink if it appears in $PATH
    rm -fv /usr/libexec/clang-analyzer/scan-build/clang
fi

if test -r /usr/lib64/gobject-introspection/giscanner/dumper.py; then
    # pretend we use GCC even if we run through scan-build; g-ir-scanner would
    # otherwise think we use MS compiler and insert compilation flags that GCC
    # does not understand
    sed -i "s/^\( *\)self._compiler_cmd =.*\$/\1self._compiler_cmd = 'gcc'/" \
        /usr/lib64/gobject-introspection/giscanner/dumper.py
fi
