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

import csmock.common.cflags
import csmock.common.util


STRACE_CAPTURE_DIR = "/builddir/strace-capture"


class PluginProps:
    def __init__(self):
        self.description = "A dynamic analysis tool that records system calls associated with a running process."

        # hook this plug-in before "gcc" to make ScanProps:enable_csexec() work
        self.pass_before = ["gcc"]


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--strace-add-flag", action="append", default=[],
            help="append the given flag when invoking strace \
(can be used multiple times)")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # make sure strace is installed in chroot
        props.install_pkgs += ["strace"]

        # record version of the installed "strace" tool
        csmock.common.util.install_default_toolver_hook(props, "strace")

        # hook csexec into the binaries produced in %build
        props.enable_csexec()

        # create directory for strace's results
        def create_cap_dir_hook(results, mock):
            return mock.exec_mockbuild_cmd("mkdir -pv '%s'" % STRACE_CAPTURE_DIR)
        props.post_depinst_hooks += [create_cap_dir_hook]

        # default strace cmd-line
        wrap_cmd_list = ["strace",
                "--output=%s/trace" % STRACE_CAPTURE_DIR,
                "--output-separately"]

        # append custom args if specified
        wrap_cmd_list += args.strace_add_flag

        # configure csexec to use strace as the execution wrapper
        wrap_cmd = csmock.common.cflags.serialize_flags(wrap_cmd_list, separator="\\a")
        extra_env = {}
        extra_env["CSEXEC_WRAP_CMD"] = wrap_cmd

        # install a hook to run %check through strace
        def run_strace_hook(results, mock, props):
            ec = mock.exec_rpmbuild_bi(props, extra_env=extra_env)
            if ec != 0:
                results.error("strace plug-in: %%install or %%check failed with exit code %d" % ec)
            return ec
        props.post_install_hooks += [run_strace_hook]

        # pick the captured files when %check is complete
        props.copy_out_files += [STRACE_CAPTURE_DIR]

        # TODO: add filter_hook to transform the captured trace files
