# Copyright (C) 2017 Red Hat, Inc.
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


RUN_BANDIT_SH = "/usr/share/csmock/scripts/run-bandit.sh"

BANDIT_CAPTURE = "/builddir/bandit-capture.err"

FILTER_CMD = "csgrep --quiet '%s' | csgrep --event '%s' > '%s'"


class PluginProps:
    def __init__(self):
        self.description = "A tool designed to find common security issues in Python code."


class Plugin:
    def __init__(self):
        self.enabled = False
        self._severity_levels = ['LOW', 'MEDIUM', 'HIGH']

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        csmock.common.util.install_script_scan_opts(parser, "bandit")
        parser.add_argument("--bandit-evt-filter", default="^B[0-9]+",
                            help="report only Bandit defects "
                                 "whose key event matches the given regex "
                                 "(defaults to '^B[0-9]+')")
        parser.add_argument("--bandit-severity-filter", default="LOW",
                            help="suppress Bandit defects whose severity level is below given level "
                                 "(default 'LOW')", choices=self._severity_levels)

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # which directories are we going to scan (build and/or install)
        dirs_to_scan = csmock.common.util.dirs_to_scan_by_args(
            parser, args, props, "bandit")

        # Note: bandit is running on python3, pbr needs git to assert correct version
        props.install_pkgs += ["bandit"]

        severity_filter = dict(zip(self._severity_levels, ['-l', '-ll', '-lll']))[args.bandit_severity_filter.upper()]
        run_cmd = f"shopt -s nullglob && {RUN_BANDIT_SH} {severity_filter} {dirs_to_scan} > {BANDIT_CAPTURE}"
        props.post_build_chroot_cmds += [run_cmd]
        props.copy_out_files += [BANDIT_CAPTURE]

        csmock.common.util.install_default_toolver_hook(props, "bandit")

        def filter_hook(results):
            src = results.dbgdir_raw + BANDIT_CAPTURE
            dst = "%s/bandit-capture.err" % results.dbgdir_uni
            cmd = FILTER_CMD % (src, args.bandit_evt_filter, dst)
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
