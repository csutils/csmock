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

# standard imports
import subprocess

# local imports
import csmock.common.util

from csmock.common.cflags import add_custom_flag_opts, flags_by_warning_level

CSGCCA_BIN="/usr/bin/csgcca"

class PluginProps:
    def __init__(self):
        self.pass_priority = 0x10


class Plugin:
    def __init__(self):
        self.enabled = False
        self.flags = flags_by_warning_level(0)
        self.description = "Plugin capturing GCC warnings, optionally with customized compiler flags."
        self.csgcca_path = None

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def enable_sanitize(self, props, pkgs, flags):
        self.enabled = True
        props.run_check = True
        props.install_pkgs += pkgs
        self.flags.append_flags(flags)

        # GCC sanitizers usually do not work well with valgrind
        props.install_pkgs_blacklist += ["valgrind"]

    def init_parser(self, parser):
        parser.add_argument(
            "-w", "--gcc-warning-level", type=int,
            help="Adjust GCC warning level.  -w0 means default flags, \
-w1 appends -Wall and -Wextra, and -w2 enables some other useful warnings. \
(automatically enables the GCC plug-in)")

        parser.add_argument(
            "--gcc-analyze", action="store_true",
            help="run `gcc -fanalyzer` in a separate process")

        parser.add_argument(
            "--gcc-analyze-add-flag", action="append", default=[],
            help="append the given flag when invoking `gcc -fanalyzer` \
(can be used multiple times)")

        parser.add_argument(
            "--gcc-set-env", action="store_true",
            help="set $CC and $CXX to gcc and g++, respectively, for build")

        # -fsanitize={address,leak} cannot be combined with -fsanitize=thread
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--gcc-sanitize-address", action="store_true",
            help="enable %%check and compile with -fsanitize=address")

        group.add_argument(
            "--gcc-sanitize-leak", action="store_true",
            help="enable %%check and compile with -fsanitize=leak")

        group.add_argument(
            "--gcc-sanitize-thread", action="store_true",
            help="enable %%check and compile with -fsanitize=thread")

        parser.add_argument(
            "--gcc-sanitize-undefined", action="store_true",
            help="enable %%check and compile with -fsanitize=undefined")

        add_custom_flag_opts(parser)

    def handle_args(self, parser, args, props):
        if args.gcc_warning_level is not None:
            self.enable()
            self.flags = flags_by_warning_level(args.gcc_warning_level)

        if args.gcc_analyze:
            self.enable()
            # resolve csgcca_path by querying csclng binary
            cmd = [CSGCCA_BIN, "--print-path-to-wrap"]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, _) = p.communicate()
            if 0 != p.returncode:
                parser.error("--gcc-analyze requires %s to be available" % CSGCCA_BIN)
            self.csgcca_path = out.decode("utf8").strip()
            props.copy_in_files += [CSGCCA_BIN, self.csgcca_path]

        if args.gcc_set_env:
            self.enable()
            props.env["CC"]  = "gcc"
            props.env["CXX"] = "g++"

        if args.gcc_sanitize_address:
            self.enable_sanitize(props, ["libasan"], ["-fsanitize=address"])

            # leak checker is currently too picky even for standard libs
            props.env["ASAN_OPTIONS"] = "detect_leaks=0"

            # -fsanitize=address does not seem to be supported with -static
            self.flags.remove_flags(["-static"])

        if args.gcc_sanitize_leak:
            self.enable_sanitize(props, ["liblsan"], ["-fsanitize=leak"])

            # -fsanitize=leak does not seem to work well with -static
            self.flags.remove_flags(["-static"])

        if args.gcc_sanitize_thread:
            self.enable_sanitize(props, ["libtsan"], ["-fsanitize=thread"])

            # -fsanitize=thread does not seem to be supported with -static
            self.flags.remove_flags(["-static"])

        if args.gcc_sanitize_undefined:
            self.enable_sanitize(props, ["libubsan", "libubsan-static"], ["-fsanitize=undefined"])

        # serialize custom compiler flags
        if self.flags.append_custom_flags(args):
            self.enable()

        if not self.enabled:
            # drop COMPILER_WARNING defects mistakenly enabled by other plug-ins
            props.cswrap_filters += \
                ["csgrep --invert-match --checker COMPILER_WARNING"]
            return

        props.enable_cswrap()
        props.cswrap_filters += \
            ["csgrep --invert-match --checker COMPILER_WARNING --event error"]

        # write all compiler flags to the environment
        self.flags.write_to_env(props.env)

        csmock.common.util.install_default_toolver_hook(props, "gcc")

        if self.csgcca_path is not None:
            def csgcca_hook(results, mock):
                cmd = "echo 'int main() {}'"
                cmd += " | gcc -xc - -c -o /dev/null"
                cmd += " -fanalyzer -fdiagnostics-path-format=separate-events"
                if 0 != mock.exec_mockbuild_cmd(cmd):
                    results.error("`gcc -fanalyzer` does not seem to work, disabling the tool", ec=0)
                    return 0

                # XXX: changing props this way is extremely fragile
                props.path = [self.csgcca_path] + props.path
                props.env["CSWRAP_TIMEOUT_FOR"] += ":gcc"
                if args.gcc_analyze_add_flag:
                    # propagate custom clang flags
                    props.env["CSGCCA_ADD_OPTS"] = csmock.common.cflags.serialize_flags(args.gcc_analyze_add_flag)

                # record that `gcc -fanalyzer` was used for this scan
                csmock.common.util.write_toolver_from_rpmlist(results, mock, "gcc", "gcc-analyzer")
                return 0

            props.post_depinst_hooks += [csgcca_hook]
