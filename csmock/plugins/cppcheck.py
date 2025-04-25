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
import re
import subprocess

# local imports
import csmock.common.cflags


class PluginProps:
    def __init__(self):
        self.description = "Static analysis tool for C/C++ code."

        # include this plug-in in `csmock --all-tools`
        self.stable = True


class Plugin:
    def __init__(self):
        self.enabled = False
        self.use_host_cppcheck = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--use-host-cppcheck", action="store_true",
            help="use statically linked cppcheck installed on the host \
(automatically enables the Cppcheck plug-in)")

        parser.add_argument(
            "--cppcheck-add-flag", action="append", default=[],
            help="append the given flag when invoking cppcheck \
(can be used multiple times)")

    def handle_args(self, parser, args, props):
        self.use_host_cppcheck = args.use_host_cppcheck
        if self.use_host_cppcheck:
            self.enable()

        if not self.enabled:
            return

        props.enable_cswrap()
        props.env["CSWRAP_TIMEOUT_FOR"] += ":cppcheck"
        props.cswrap_filters += ["csgrep --mode=json --invert-match \
--checker CPPCHECK_WARNING \
--event 'cppcheckError|internalAstError|normalCheckLevelMaxBranches|preprocessorErrorDirective|syntaxError|unknownMacro'"]

        if args.cppcheck_add_flag:
            # propagate custom cppcheck flags
            props.env["CSCPPC_ADD_OPTS"] = csmock.common.cflags.serialize_flags(args.cppcheck_add_flag)

        # resolve cscppc_path by querying cscppc binary
        cmd = ["cscppc", "--print-path-to-wrap"]
        subproc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = subproc.communicate()
        cscppc_path = out.decode("utf8").strip()

        props.path = [cscppc_path] + props.path
        props.copy_in_files += \
                ["/usr/bin/cscppc", cscppc_path, "/usr/share/cscppc"]

        if self.use_host_cppcheck:
            # install only tinyxml2 (if acutally required by cppcheck)
            cmd = "rpm -q cppcheck --requires | grep tinyxml2 > /dev/null"
            if os.system(cmd) == 0:
                props.install_pkgs += ["tinyxml2"]

            # copy cppcheck's executable into the chroot
            props.copy_in_files += ["/usr/bin/cppcheck"]

            # copy cppcheck's data files into the chroot
            if os.path.isdir("/usr/share/Cppcheck"):
                props.copy_in_files += ["/usr/share/Cppcheck"]
            if os.path.isdir("/usr/share/cppcheck"):
                props.copy_in_files += ["/usr/share/cppcheck"]
        else:
            # install cppcheck into the chroot
            props.install_pkgs += ["cppcheck"]

        def store_cppcheck_version_hook(results, mock):
            cmd = mock.get_mock_cmd(["--chroot", "cppcheck --version"])
            (ec, verstr) = results.get_cmd_output(cmd, shell=False)
            if ec != 0:
                if self.use_host_cppcheck:
                    results.error("--use-host-cppcheck expects statically linked cppcheck installed on the host", ec=0)
                results.error("failed to query cppcheck version", ec=ec)
                return ec

            ver = re.sub("^Cppcheck ", "", verstr.strip())
            results.ini_writer.append("analyzer-version-cppcheck", ver)
            return 0

        props.post_depinst_hooks += [store_cppcheck_version_hook]
