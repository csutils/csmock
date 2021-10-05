# Copyright (C) 2021 Red Hat, Inc.
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


UNICONTROL_SCRIPT = "/usr/share/csmock/scripts/find-unicode-control.py"

UNICONTROL_SCAN_DIR = "/builddir/build/BUILD"

UNICONTROL_OUTPUT = "/builddir/unicontrol-capture.err"

UNICONTROL_LOG = "/builddir/unicontrol-capture.log"

FILTER_CMD = "csgrep --mode=json '%s' > '%s'"


class PluginProps:
    def __init__(self):
        self.description = "[TODO] experimental csmock plug-in"


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--unicontrol-bidi-only", action="store_true",
            help="look for bidirectional control characters only")

        parser.add_argument(
            "--unicontrol-notests", action="store_true",
            help="exclude tests (basically test.* as a component of path)")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # update scan metadata
        def write_toolver_hook(results):
            results.ini_writer.append("analyzer-version-unicontrol", "0.0.1")
            return 0
        props.pre_mock_hooks += [write_toolver_hook]

        # dependency of UNICONTROL_SCRIPT
        props.install_pkgs += ["python3-magic", "python3-six"]

        cmd = "LANG=en_US.utf8 %s -v %s" % (UNICONTROL_SCRIPT, UNICONTROL_SCAN_DIR)

        if args.unicontrol_bidi_only:
            cmd += " -p bidi"

        if args.unicontrol_notests:
            cmd += " --notests"

        cmd += " >%s 2>%s" % (UNICONTROL_OUTPUT, UNICONTROL_LOG)
        props.post_build_chroot_cmds += [cmd]
        props.copy_out_files += [UNICONTROL_OUTPUT, UNICONTROL_LOG]

        def filter_hook(results):
            src = results.dbgdir_raw + UNICONTROL_OUTPUT
            dst = "%s/unicontrol-capture.js" % results.dbgdir_uni
            cmd = FILTER_CMD % (src, dst)
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
