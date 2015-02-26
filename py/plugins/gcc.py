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

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument("-w", "--gcc-warning-level", type=int,
                help="Adjust GCC warning level.  -w0 means default flags, \
-w1 appends -Wall and -Wextra, and -w2 enables some other useful warnings. \
(automatically enables the GCC plug-in)")

    def handle_args(self, parser, args, props):
        if args.gcc_warning_level is not None:
            self.enable()
            self.flags |= flags_by_warning_level(args.gcc_warning_level)

        if not self.enabled:
            # drop COMPILER_WARNING defects mistakenly enabled by other plug-ins
            props.cswrap_filters += \
                ["csgrep --invert-match --checker COMPILER_WARNING"]
            return

        props.enable_cswrap()
        props.cswrap_filters += \
            ["csgrep --invert-match --checker COMPILER_WARNING --event error"]

        self.flags.write_to_env(props.env)

        csmock.common.util.install_default_toolver_hook(props, "gcc")
