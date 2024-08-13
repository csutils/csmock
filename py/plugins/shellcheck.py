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

import csmock.common.util


RUN_SHELLCHECK_SH = "/usr/share/csmock/scripts/run-shellcheck.sh"

SHELLCHECK_CAP_DIR = "/builddir/shellcheck-results"

FILTER_CMD = "csgrep --mode=json --remove-duplicates --quiet " \
        "--invert-match --event '^note|warning\\[SC1090\\]'"

# default maximum number of scripts scanned by a single shellcheck process
DEFAULT_SC_BATCH = 1

# default maximum amount of wall-clock time taken by a single shellcheck process [s]
DEFAULT_SC_TIMEOUT = 30


class PluginProps:
    def __init__(self):
        self.description = "A static analysis tool that gives warnings and suggestions for bash/sh shell scripts."

        # include this plug-in in `csmock --all-tools`
        self.stable = True


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        csmock.common.util.install_script_scan_opts(parser, "shellcheck")
        parser.add_argument(
            "--shellcheck-batch", type=int, default=DEFAULT_SC_BATCH,
            help="maximum number of scripts scanned by a single shellcheck process" \
                f" (defaults to {DEFAULT_SC_BATCH})")
        parser.add_argument(
            "--shellcheck-timeout", type=int, default=DEFAULT_SC_TIMEOUT,
            help="maximum amount of wall-clock time taken by a single shellcheck process [s]" \
                f" (defaults to {DEFAULT_SC_TIMEOUT})")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # which directories are we going to scan (build and/or install)
        dirs_to_scan = csmock.common.util.dirs_to_scan_by_args(
            parser, args, props, "shellcheck")

        # append "/*" to each directory in dirs_to_scan (to scan pkg-specific dirs)
        dirs_to_scan = " ".join([dir + "/*" for dir in dirs_to_scan.split()])

        props.install_pkgs += ["ShellCheck"]
        cmd = f"SC_RESULTS_DIR={SHELLCHECK_CAP_DIR} "
        cmd += f"SC_BATCH={args.shellcheck_batch} "
        cmd += f"SC_TIMEOUT={args.shellcheck_timeout} "
        cmd += f"{RUN_SHELLCHECK_SH} {dirs_to_scan}"
        props.post_build_chroot_cmds += [cmd]
        props.copy_out_files += [SHELLCHECK_CAP_DIR]

        csmock.common.util.install_default_toolver_hook(props, "ShellCheck")

        def filter_hook(results):
            src = os.path.join(results.dbgdir_raw, SHELLCHECK_CAP_DIR[1:])
            dst = os.path.join(results.dbgdir_uni, "shellcheck-capture.json")
            cmd = f"cd {src} && {FILTER_CMD} *.json > {dst}"
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
