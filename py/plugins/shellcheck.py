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


RUN_SHELLCHECK_SH = "/usr/share/csmock/scripts/run-shellcheck.sh"

SHELLCHECK_CAPTURE = "/builddir/shellcheck-capture.err"

FILTER_CMD = "csgrep --quiet '%s' " \
        "| csgrep --invert-match --event '^note|warning\\[SC1090\\]' " \
        "> '%s'"


class PluginProps:
    def __init__(self):
        self.pass_priority = 0x58
        self.description = "A static analysis tool that gives warnings and suggestions for bash/sh shell scripts."


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        csmock.common.util.install_script_scan_opts(parser, "shellcheck")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # which directories are we going to scan (build and/or install)
        dirs_to_scan = csmock.common.util.dirs_to_scan_by_args(
            parser, args, props, "shellcheck")

        props.install_pkgs += ["ShellCheck"]
        props.copy_in_files += [RUN_SHELLCHECK_SH]
        cmd = "%s %s > %s" % (RUN_SHELLCHECK_SH, dirs_to_scan, SHELLCHECK_CAPTURE)
        props.post_build_chroot_cmds += [cmd]
        props.copy_out_files += [SHELLCHECK_CAPTURE]

        csmock.common.util.install_default_toolver_hook(props, "ShellCheck")

        def filter_hook(results):
            src = results.dbgdir_raw + SHELLCHECK_CAPTURE
            dst = "%s/shellcheck-capture.err" % results.dbgdir_uni
            cmd = FILTER_CMD % (src, dst)
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
