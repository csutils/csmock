# Copyright (C) 2014-2023 Red Hat, Inc.
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
import os
import subprocess

# local imports
import csmock.common.util

from csmock.common.cflags import add_custom_flag_opts, flags_by_warning_level

CSGCCA_BIN = "/usr/bin/csgcca"

# directory for GCC results (currently used only with `--gcc-analyzer-bin`)
GCC_RESULTS_DIR = "/builddir/gcc-results"

CSMOCK_GCC_WRAPPER_NAME = 'csmock-gcc-wrapper'
CSMOCK_GCC_WRAPPER_PATH = '/usr/bin/%s' % CSMOCK_GCC_WRAPPER_NAME

# script to run gcc analyzer and dump its output to a seaprate SARIF file in GCC_RESULTS_DIR
CSMOCK_GCC_WRAPPER_TEMPLATE = f"""#!/bin/bash
fn=$(flock {GCC_RESULTS_DIR} mktemp "{GCC_RESULTS_DIR}/$$-XXXX.sarif")
exec %s "$@" -fdiagnostics-set-output="sarif:file=$fn"
"""

# command to read and join all captured SARIF files
FILTER_CMD = "csgrep --mode=json --remove-duplicates"

SANITIZER_CAPTURE_DIR = "/builddir/gcc-sanitizer-capture"

class PluginProps:
    def __init__(self):
        self.description = "Plugin capturing GCC warnings, optionally with customized compiler flags."

        # include this plug-in in `csmock --all-tools`
        self.stable = True


class Plugin:
    def __init__(self):
        self.enabled = False
        self.sanitize = False
        self.flags = flags_by_warning_level(0)
        self.csgcca_path = None

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def enable_sanitize(self, props, pkgs, flags):
        self.enabled = True
        self.sanitize = True
        props.install_pkgs += pkgs
        self.flags.append_flags(flags)

        # FIXME: too hacky, strip lib prefix from the name
        name = pkgs[0][3:]

        # save logs to specified files
        props.env[f"{name.upper()}_OPTIONS"] = \
                  f"log_path={SANITIZER_CAPTURE_DIR}/{name}"

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
            "--gcc-analyzer-bin", action="store",
            help="Use custom build of gcc to perform scan. \
            Absolute path to the binary must be provided.")

        parser.add_argument(
            "--gcc-analyze-add-flag", action="append", default=[],
            help="append the given flag when invoking `gcc -fanalyzer` \
(can be used multiple times)")

        parser.add_argument(
            "--gcc-set-env", action="store_true",
            help="set $CC and $CXX to gcc and g++, respectively, for build")

        # -fsanitize={address,leak} cannot be combined with -fsanitize=thread
        # generally, more sanitizer libraries cannot be combined because
        # the collection results would be unreliable:
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=94328
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

        group.add_argument(
            "--gcc-sanitize-undefined", action="store_true",
            help="enable %%check and compile with -fsanitize=undefined")

        add_custom_flag_opts(parser)

    def handle_args(self, parser, args, props):
        if args.gcc_warning_level is not None:
            self.enable()
            self.flags = flags_by_warning_level(args.gcc_warning_level)

        if args.gcc_analyze or \
                args.gcc_analyzer_bin or \
                getattr(args, "all_tools", False):
            self.enable()

            if args.gcc_analyzer_bin and not args.gcc_analyzer_bin.startswith("/"):
                parser.error("--gcc-analyzer-bin should be an absolute path. "
                             "Found value: '%s'." % args.gcc_analyzer_bin)

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
            props.env["ASAN_OPTIONS"] += ",detect_leaks=0"

            # detect usage of already destroyed stack variables
            props.env["ASAN_OPTIONS"] += ",detect_stack_use_after_return=1"

            # -fsanitize=address does not seem to be supported with -static
            self.flags.remove_flags(["-static"])

            # preload ASAN for %check
            def run_asan_hook(results, mock, props):
                cmd = "echo /usr/lib64/libasan.so.*.* > /etc/ld.so.preload"
                rv = mock.exec_chroot_cmd(cmd)
                if 0 != rv:
                    results.error(f"ASAN plug-in: ASAN preloading failed with exit code {rv}")
                    return rv

                # FIXME: hack
                extra_env = {"ASAN_OPTIONS": props.env["ASAN_OPTIONS"] + ",verify_asan_link_order=0"}
                ec = mock.exec_rpmbuild_bi(props, extra_env=extra_env)
                if 0 != ec:
                    results.error(f"ASAN plug-in: %install or %check failed with exit code {rv}")
                return ec

            props.post_install_hooks += [run_asan_hook]

        if args.gcc_sanitize_leak:
            self.enable_sanitize(props, ["liblsan"], ["-fsanitize=leak"])

            # execute %check section
            props.run_check = True

            # -fsanitize=leak does not seem to work well with -static
            self.flags.remove_flags(["-static"])

        if args.gcc_sanitize_thread:
            self.enable_sanitize(props, ["libtsan"], ["-fsanitize=thread"])

            # execute %check section
            props.run_check = True

            # -fsanitize=thread does not seem to be supported with -static
            self.flags.remove_flags(["-static"])

        if args.gcc_sanitize_undefined:
            self.enable_sanitize(props, ["libubsan", "libubsan-static"], ["-fsanitize=undefined"])

            # execute %check section
            props.run_check = True

            # print full stack traces
            props.env["UBSAN_OPTIONS"] += ",print_stacktrace=1"

        # serialize custom compiler flags
        if self.flags.append_custom_flags(args):
            self.enable()

        if not self.enabled:
            # drop COMPILER_WARNING defects mistakenly enabled by other plug-ins
            props.cswrap_filters += \
                ["csgrep --mode=json --invert-match --checker COMPILER_WARNING"]
            return

        if self.sanitize:
            if "valgrind" in props.install_pkgs:
                parser.error("GCC sanitizers are not compatible with valgrind")

            # %check should not be enabled for ASAN
            if args.gcc_sanitize_address:
                assert not props.run_check

            self.flags.append_flags(['-g', '-fno-omit-frame-pointer',
                                     '-fsanitize-recover=all'])

            # sanitizers are not compatible with _FORTIFY_SOURCE
            # https://github.com/google/sanitizers/issues/247#issuecomment-1283500316
            self.flags.remove_flags(["-D_FORTIFY_SOURCE=*"])

            # silence annobin's complaints about missing _FORTIFY_SOURCE defines
            props.rpm_opts += ["--undefine", "_annotated_build"]

            # create directory for sanitizer's results
            def create_cap_dir_hook(results, mock):
                cmd = f"mkdir -pv '{SANITIZER_CAPTURE_DIR}'"
                return mock.exec_mockbuild_cmd(cmd)
            props.post_depinst_hooks += [create_cap_dir_hook]

            # pick the captured files when %check is complete
            props.copy_out_files += [SANITIZER_CAPTURE_DIR]

        # make sure gcc is installed in the chroot
        props.install_pkgs += ["gcc"]

        props.enable_cswrap()
        props.cswrap_filters += \
            ["csgrep --mode=json --invert-match --checker COMPILER_WARNING --event error"]

        # write all compiler flags to the environment
        self.flags.write_to_env(props.env)

        csmock.common.util.install_default_toolver_hook(props, "gcc")

        if self.csgcca_path is not None:
            def csgcca_hook(results, mock):
                analyzer_bin = args.gcc_analyzer_bin if args.gcc_analyzer_bin else "gcc"
                cmd = "echo 'int main() {}'"
                cmd += " | %s -xc - -c -o /dev/null" % analyzer_bin
                cmd += " -fanalyzer -fdiagnostics-path-format=separate-events"
                if 0 != mock.exec_mockbuild_cmd(cmd):
                    results.error("`%s -fanalyzer` does not seem to work, "
                                  "disabling the tool" % analyzer_bin, ec=0)
                    return 0

                # use -fdiagnostics-text-art-charset=none if supported by gcc in the chroot
                flag = "-fdiagnostics-text-art-charset=none"
                if 0 == mock.exec_mockbuild_cmd(f"{cmd} {flag}"):
                    props.env["CSGCCA_ADD_OPTS"] = flag

                if args.gcc_analyzer_bin:
                    # create an executable shell script to wrap the custom gcc binary
                    wrapper_script = CSMOCK_GCC_WRAPPER_TEMPLATE % analyzer_bin
                    cmd = "echo '%s' > %s && chmod 755 %s" % \
                          (wrapper_script,
                           CSMOCK_GCC_WRAPPER_PATH,
                           CSMOCK_GCC_WRAPPER_PATH)
                    rv = mock.exec_chroot_cmd(cmd)
                    if 0 != rv:
                        results.error("failed to create csmock gcc wrapper script")
                        return rv

                    # wrap the shell script by cswrap to capture output of `gcc -fanalyzer`
                    cmd = "ln -sf ../../bin/cswrap %s/%s" % \
                          (props.cswrap_path, CSMOCK_GCC_WRAPPER_NAME)
                    rv = mock.exec_chroot_cmd(cmd)
                    if 0 != rv:
                        results.error("failed to create csmock gcc wrapper symlink")
                        return rv

                    # tell csgcca to use the wrapped script rather than system gcc analyzer
                    props.env["CSGCCA_ANALYZER_BIN"] = CSMOCK_GCC_WRAPPER_NAME

                    # create directory for gcc results
                    def create_gcc_results_dir_hook(_, mock):
                        cmd = f"mkdir -pv '{GCC_RESULTS_DIR}' && touch '{GCC_RESULTS_DIR}/empty.sarif'"
                        return mock.exec_mockbuild_cmd(cmd)
                    props.post_depinst_hooks += [create_gcc_results_dir_hook]

                    # copy gcc results out of the chroot
                    props.copy_out_files += [GCC_RESULTS_DIR]

                    # process all captured SARIF files
                    def filter_hook(results):
                        src = os.path.join(results.dbgdir_raw, GCC_RESULTS_DIR[1:])
                        dst = os.path.join(results.dbgdir_uni, "gcc-results.json")
                        cmd = f'{FILTER_CMD} --file-glob "{src}/*.sarif" > "{dst}"'
                        return results.exec_cmd(cmd, shell=True)
                    props.post_process_hooks += [filter_hook]

                # XXX: changing props this way is extremely fragile
                # insert csgcca right before cswrap to avoid chaining
                # csclng/cscppc while invoking `gcc -fanalyzer`
                idx_cswrap = 0
                for idx in range(0, len(props.path)):
                    if props.path[idx].endswith("/cswrap"):
                        idx_cswrap = idx
                        break
                props.path.insert(idx_cswrap, self.csgcca_path)

                props.env["CSWRAP_TIMEOUT_FOR"] += ":%s" % (CSMOCK_GCC_WRAPPER_NAME if args.gcc_analyzer_bin else "gcc")
                if args.gcc_analyze_add_flag:
                    # propagate custom GCC analyzer flags
                    props.env["CSGCCA_ADD_OPTS"] = csmock.common.cflags.serialize_flags(args.gcc_analyze_add_flag)

                # record that `gcc -fanalyzer` was used for this scan
                cmd = mock.get_mock_cmd(["--chroot", "%s --version" % analyzer_bin])
                (rc, ver) = results.get_cmd_output(cmd, shell=False)
                if rc != 0:
                    return rc
                ver = ver.partition('\n')[0].strip()
                ver = ver.split(' ')[2]
                csmock.common.util.write_toolver(results.ini_writer, "gcc-analyzer", ver)

                return 0

            props.post_depinst_hooks += [csgcca_hook]

        # transform log files produced by UBSAN into csdiff format
        if args.gcc_sanitize_undefined:
            def ubsan_filter_hook(results):
                src_dir = results.dbgdir_raw + SANITIZER_CAPTURE_DIR

                # ensure we have permission to read all capture files
                results.exec_cmd(['chmod', '-R', '+r', src_dir])

                # `cd` first to avoid `csgrep: Argument list too long` error on glob expansion
                dst = f"{results.dbgdir_uni}/ubsan-capture.js"
                cmd = f"cd '{src_dir}' && touch ubsan.empty && csgrep --mode=json --remove-duplicates ubsan.* > '{dst}'"
                return results.exec_cmd(cmd, shell=True)

            props.post_process_hooks += [ubsan_filter_hook]
