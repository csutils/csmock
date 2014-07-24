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
import subprocess

class PluginProps:
    def __init__(self):
        self.pass_priority = 0x20

class Plugin:
    def __init__(self):
        self.enabled = False
        self.use_host_cppcheck = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument("--use-host-cppcheck", action="store_true",
                help="use host's Cppcheck instead of the one in chroot \
(automatically enables the Cppcheck plug-in)")

    def handle_args(self, parser, args, props):
        self.use_host_cppcheck = args.use_host_cppcheck
        if self.use_host_cppcheck:
            self.enable()

        if not self.enabled:
            return

        props.enable_cswrap()
        props.cswrap_filters += ["csgrep --invert-match \
--checker CPPCHECK_WARNING \
--event 'preprocessorErrorDirective|syntaxError'"]

        # resolve cscppc_path by querying csmock binary
        cmd = ["cscppc", "--print-path-to-wrap"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        cscppc_path = out.strip()

        props.path = [cscppc_path] + props.path
        props.copy_in_files += \
                ["/usr/bin/cscppc", cscppc_path, "/usr/share/cscppc"]

        if self.use_host_cppcheck:
            # install only tinyxml2 (if acutally required by cppcheck)
            cmd = "rpm -q cppcheck --requires | grep tinyxml2 > /dev/null"
            if os.system(cmd) == 0:
                props.install_pkgs += ["tinyxml2"]

            # copy cppcheck's binaries into the chroot
            props.copy_in_files += ["/usr/bin/cppcheck"]
            if os.path.isdir("/usr/share/cppcheck"):
                props.copy_in_files += ["/usr/share/cppcheck"]
        else:
            # install cppcheck into the chroot
            props.install_pkgs += ["cppcheck"]
