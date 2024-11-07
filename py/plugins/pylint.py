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


RUN_PYLINT_SH = "/usr/share/csmock/scripts/run-pylint.sh"

PYLINT_CAPTURE = "/builddir/pylint-capture.err"

FILTER_CMD = "csgrep --quiet '%s' " \
        "| csgrep --event '%s' " \
        "> '%s'"


class PluginProps:
    def __init__(self):
        self.description = "Python source code analyzer which looks for programming errors."


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        csmock.common.util.install_script_scan_opts(parser, "pylint")
        parser.add_argument(
            "--pylint-evt-filter", default="^W[0-9]+",
            help="filter out Pylint defects whose key event matches the given regex \
(defaults to '^W[0-9]+', use '.*' to get all defects detected by Pylint)")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # which directories are we going to scan (build and/or install)
        dirs_to_scan = csmock.common.util.dirs_to_scan_by_args(
            parser, args, props, "pylint")

        props.install_pkgs += ["pylint"]
        cmd = f"shopt -s nullglob && {RUN_PYLINT_SH} {dirs_to_scan} > {PYLINT_CAPTURE}"
        props.post_build_chroot_cmds += [cmd]
        props.copy_out_files += [PYLINT_CAPTURE]

        csmock.common.util.install_default_toolver_hook(props, "pylint")

        def filter_hook(results):
            src = results.dbgdir_raw + PYLINT_CAPTURE
            dst = "%s/pylint-capture.err" % results.dbgdir_uni
            cmd = FILTER_CMD % (src, args.pylint_evt_filter, dst)
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
