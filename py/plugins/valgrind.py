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


VALGRIND_CAPTURE_DIR = "/builddir/valgrind-capture"


class PluginProps:
    def __init__(self):
        # FIXME: This needs to be lower than priority of the "gcc" plugin
        # for ScanProps::enable_csexec() to work.
        self.pass_priority = 0x01


class Plugin:
    def __init__(self):
        self.enabled = False
        self.description = "A dynamic analysis tool for finding memory management bugs in programs."

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--valgrind-add-flag", action="append", default=[],
            help="append the given flag when invoking valgrind \
(can be used multiple times)")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # make sure valgrind is installed in chroot
        props.install_pkgs += ["valgrind"]

        # record version of the installed "valgrind" tool
        csmock.common.util.install_default_toolver_hook(props, "valgrind")

        # hook csexec into the binaries produced in %build
        props.enable_csexec()

        # create directory for valgrind's results
        def create_cap_dir_hook(results, mock):
            return mock.exec_mockbuild_cmd("mkdir -pv '%s'" % VALGRIND_CAPTURE_DIR)
        props.post_depinst_hooks += [create_cap_dir_hook]

        # default valgrind cmd-line
        wrap_cmd_list = ["valgrind",
                "--xml=yes",
                "--xml-file=%s/pid-%%p-%%n.xml" % VALGRIND_CAPTURE_DIR,
                "--log-file=%s/pid-%%p-%%n.log" % VALGRIND_CAPTURE_DIR,
                "--child-silent-after-fork=yes"]

        # append custom args if specified
        wrap_cmd_list += args.valgrind_add_flag

        # FIXME: multiple runs of %check for multiple dynamic analyzers not yet supported
        assert "CSEXEC_WRAP_CMD" not in props.env

        # configure csexec to use valgrind as the execution wrapper
        wrap_cmd = csmock.common.cflags.serialize_flags(wrap_cmd_list, separator="\\a")
        props.env["CSEXEC_WRAP_CMD"] = wrap_cmd

        # run %check (disabled by default for static analyzers)
        props.run_check = True

        # pick the captured files when %check is complete
        props.copy_out_files += [VALGRIND_CAPTURE_DIR]

        # delete empty log files
        def cleanup_hook(results):
            return results.exec_cmd(["find", results.dbgdir_raw + VALGRIND_CAPTURE_DIR,
                "-name", "pid-*.log", "-empty", "-delete"])
        props.post_process_hooks += [cleanup_hook]

        # transform XML files produced by valgrind into csdiff format
        def filter_hook(results):
            src_dir = results.dbgdir_raw + VALGRIND_CAPTURE_DIR
            dst = "%s/valgrind-capture.js" % results.dbgdir_uni
            cmd = "csgrep --mode=json --quiet --remove-duplicates '%s'/*.xml > '%s'" \
                    % (src_dir, dst)
            return results.exec_cmd(cmd, shell=True)
        props.post_process_hooks += [filter_hook]
