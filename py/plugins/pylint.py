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

run_pylint_sh = "/usr/share/csmock/scripts/run-pylint.sh"

dirs_to_scan = "/builddir/build/BUILDROOT"

pylint_capture = "/builddir/pylint-capture.err"

filter_cmd = "csgrep --quiet '%s' " \
        "| sed 's|^/builddir/build/BUILDROOT/[^/]*/|/builddir/build/BUILD//|' " \
        "| csgrep --event '^W[0-9]+' " \
        "| cssort " \
        "> '%s'"

class PluginProps:
    def __init__(self):
        self.pass_priority = 0x50

class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        # TODO
        pass

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        props.install_pkgs += ["pylint"]
        props.copy_in_files += [run_pylint_sh]
        props.need_rpm_bi = True
        cmd = "%s %s > %s" % (run_pylint_sh, dirs_to_scan, pylint_capture)
        props.post_build_chroot_cmds += [cmd]
        props.copy_out_files += [pylint_capture]

        def filter_hook(results):
            src = results.dbgdir_raw + pylint_capture
            dst = "%s/pylint-capture.err" % results.dbgdir_uni
            cmd = filter_cmd % (src, dst)
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
