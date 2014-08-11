#!/usr/bin/env python

# Copyright (C) 2014 Red Hat, Inc.
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

import os
import re

class PluginProps:
    def __init__(self):
        self.pass_priority = 0x30

class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        # TODO: introduce options to enable/disable checkers
        pass

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        props.enable_cswrap()
        props.env["CSWRAP_TIMEOUT_FOR"] += ":clang:clang++"
        props.cswrap_filters += \
                ["csgrep --invert-match --checker CLANG_WARNING --event error"]

        props.install_pkgs += ["clang-analyzer", "imake"]

        props.copy_in_files += ["/usr/share/csmock/scripts/fixups-clang.sh"]

        props.build_cmd_wrappers += ["scan-build -plist %s"]

        # needed for the krb5 package, which overrides $CC by the __cc RPM macro
        props.rpm_opts += [
                "--define",  "__cc /usr/libexec/clang-analyzer/scan-build/ccc-analyzer",
                "--define", "__cxx /usr/libexec/clang-analyzer/scan-build/c++-analyzer"]

        def store_clang_version_hook(results, mock):
            cmd = "grep '^clang-[0-9]' %s/rpm-list-mock.txt" % results.dbgdir
            (rc, nvr) = results.get_cmd_output(cmd)
            if 0 != rc:
                return rc

            ver = re.sub("-[0-9].*$", "", re.sub("^clang-", "", nvr.strip()))
            results.ini_writer.append("analyzer-version-clang", ver)
            return 0

        props.post_depinst_hooks += [store_clang_version_hook]
