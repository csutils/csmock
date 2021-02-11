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

# standard imports
import os
import subprocess

# local imports
import csmock.common.cflags
import csmock.common.util


class PluginProps:
    def __init__(self):
        self.pass_priority = 0x30
        self.description = "Source code analysis tool that finds bugs in C, C++, and Objective-C programs."


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--clang-add-flag", action="append", default=[],
            help="append the given flag when invoking clang static analyzer \
(can be used multiple times)")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        props.enable_cswrap()
        props.env["CSWRAP_TIMEOUT_FOR"] += ":clang:clang++"
        if args.clang_add_flag:
            # propagate custom clang flags
            props.env["CSCLNG_ADD_OPTS"] = csmock.common.cflags.serialize_flags(args.clang_add_flag)

        props.cswrap_filters += \
                ["csgrep --mode=json --invert-match --checker CLANG_WARNING --event error"]

        props.install_pkgs += ["clang"]

        # resolve csclng_path by querying csclng binary
        cmd = ["csclng", "--print-path-to-wrap"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        csclng_path = out.decode("utf8").strip()

        props.path = [csclng_path] + props.path
        props.copy_in_files += \
                ["/usr/bin/csclng", csclng_path]
        if os.path.exists("/usr/bin/csclng++"):
            props.copy_in_files += ["/usr/bin/csclng++"]

        csmock.common.util.install_default_toolver_hook(props, "clang")
