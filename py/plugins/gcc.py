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

import csmock.common.util

from csmock.common.cflags import flags_by_warning_level

class PluginProps:
    def __init__(self):
        self.pass_priority = 0x10

def flags_by_default():
    return flags_by_warning_level(0)

class Plugin:
    def __init__(self):
        self.enabled = False
        self.flags = flags_by_default()
        self.description = "Plugin capturing GCC warnings.\n" \
                           "Optionally with customized compiler flags"

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument("-w", "--gcc-warning-level", type=int,
                help="Adjust GCC warning level.  -w0 means default flags, \
-w1 appends -Wall and -Wextra, and -w2 enables some other useful warnings. \
(automatically enables the GCC plug-in)")

        parser.add_argument("--gcc-add-flag", action="append", default=[],
                help="append the given compiler flag when invoking gcc \
(can be used multiple times)")

        parser.add_argument("--gcc-add-c-only-flag", action="append", default=[],
                help="append the given compiler flag when invoking gcc for C \
(can be used multiple times)")

        parser.add_argument("--gcc-add-cxx-only-flag", action="append", default=[],
                help="append the given compiler flag when invoking gcc for C++ \
(can be used multiple times)")

    def handle_args(self, parser, args, props):
        if args.gcc_warning_level is not None:
            self.enable()
            self.flags |= flags_by_warning_level(args.gcc_warning_level)

        # serialize custom compiler flags
        add_cflags = ""
        add_cxxflags = ""
        for flag in args.gcc_add_flag:
            add_cflags += ":" + flag
            add_cxxflags += ":" + flag
        for flag in args.gcc_add_c_only_flag:
            add_cflags += ":" + flag
        for flag in args.gcc_add_cxx_only_flag:
            add_cxxflags += ":" + flag
        if 0 < len(add_cflags) or 0 < len(add_cxxflags):
            self.enable()

        if not self.enabled:
            # drop COMPILER_WARNING defects mistakenly enabled by other plug-ins
            props.cswrap_filters += \
                ["csgrep --invert-match --checker COMPILER_WARNING"]
            return

        props.enable_cswrap()
        props.cswrap_filters += \
            ["csgrep --invert-match --checker COMPILER_WARNING --event error"]

        # write all compiler flags to the environment
        self.flags.write_to_env(props.env)
        props.env["CSWRAP_ADD_CFLAGS"] += add_cflags
        props.env["CSWRAP_ADD_CXXFLAGS"] += add_cxxflags

        csmock.common.util.install_default_toolver_hook(props, "gcc")
