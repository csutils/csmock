# Copyright (C) 2014 - 2018 Red Hat, Inc.
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

# standard imports
import os
import subprocess

# local imports
import csmock.common.util


class PluginProps:
    def __init__(self):
        self.pass_priority = 0x38
        self.experimental = True
        self.description = "Source code analysis for C, based on sparse."


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
        props.env["CSWRAP_TIMEOUT_FOR"] += ":smatch"
        props.cswrap_filters += \
                ["csgrep --mode=json --invert-match --checker SMATCH_WARNING --event error"]

        props.install_pkgs += ["smatch"]

        # resolve csmatch_path by querying csmatch binary
        cmd = ["csmatch", "--print-path-to-wrap"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        csmatch_path = out.decode("utf8").strip()

        props.path = [csmatch_path] + props.path
        props.copy_in_files += ["/usr/bin/csmatch", csmatch_path]

        csmock.common.util.install_default_toolver_hook(props, "smatch")
