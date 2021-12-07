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
from csmock.common.cflags import flags_by_warning_level


CBMC_CAPTURE_DIR = "/builddir/cbmc-capture"

DEFAULT_CBMC_TIMEOUT = 42


class PluginProps:
    def __init__(self):
        self.description = "Bounded Model Checker for C and C++ programs"

        # hook this plug-in before "gcc" to make ScanProps:enable_csexec() work
        self.pass_before = ["gcc"]


class Plugin:
    def __init__(self):
        self.enabled = False
        self.flags = flags_by_warning_level(0)

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--cbmc-add-flag", action="append", default=[],
            help="append the given flag when invoking cbmc \
(can be used multiple times)")

        parser.add_argument(
            "--cbmc-timeout", type=int, default=DEFAULT_CBMC_TIMEOUT,
            help="maximal amount of time taken by analysis of a single process [s]")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # make sure cbmc and its helper scripts are installed in chroot
        props.install_pkgs += ["cbmc", "cbmc-utils"]

        # record version of the installed "cbmc" tool
        csmock.common.util.install_default_toolver_hook(props, "cbmc")

        # enable cswrap
        props.enable_cswrap()
        props.cswrap_filters += ["csgrep --mode=json --invert-match --checker GCC_WARNING --event error"]

        # set dioscc as the default compiler
        # FIXME: this is not 100% reliable
        # FIXME: goto-gcc does not seem to be able to compile C++
        props.env["CC"]  = "goto-gcc"
        props.env["CXX"] = "goto-gcc"
        props.rpm_opts += ["--define", "__cc goto-gcc", "--define", "__cxx goto-gcc", "--define", "__cpp goto-gcc -E"]

        # nuke default options
        props.rpm_opts += ["--define", "optflags -O0", "--define", "build_ldflags -O0"]

        # hook csexec into the binaries produced in %build
        props.enable_csexec()

        # create directory for cbmc's results
        def create_cap_dir_hook(results, mock):
            cmd = "mkdir -pv '%s'" % CBMC_CAPTURE_DIR
            return mock.exec_mockbuild_cmd(cmd)
        props.post_depinst_hooks += [create_cap_dir_hook]

        # default cbmc cmd-line
        wrap_cmd_list = [
                "--skip-ld-linux",
                "/usr/bin/csexec-cbmc",
                "-t", "%d" % args.cbmc_timeout,
                "-l", CBMC_CAPTURE_DIR,
                "-c","--unwind 1 --json-ui --verbosity 4 --pointer-overflow-check --memory-leak-check"]

        # append custom args if specified
        # FIXME: what about single arguments with whitespaces?
        wrap_cmd_list[-1] += " " + " ".join(args.cbmc_add_flag)

        # FIXME: multiple runs of %check for multiple dynamic analyzers not yet supported
        assert "CSEXEC_WRAP_CMD" not in props.env

        # configure csexec to use cbmc as the execution wrapper
        wrap_cmd = csmock.common.cflags.serialize_flags(wrap_cmd_list, separator="\\a")
        props.env["CSEXEC_WRAP_CMD"] = wrap_cmd

        # write all compiler flags to the environment
        self.flags.append_flags(['-Wno-unknown-warning-option', '-O0', '-g', '-Wl,--dynamic-linker,/usr/bin/csexec-loader'])
        self.flags.remove_flags(['-O1', '-O2', '-O3', '-Os', '-Ofast', '-Og'])
        self.flags.write_to_env(props.env)

        # run %check (disabled by default for static analyzers)
        props.run_check = True

        # pick the captured files when %check is complete
        props.copy_out_files += [CBMC_CAPTURE_DIR]

        # transform XML files produced by cbmc into csdiff format
        def filter_hook(results):
            src_dir = results.dbgdir_raw + CBMC_CAPTURE_DIR

            # ensure we have permission to read all capture files
            results.exec_cmd(['chmod', '-R', '+r', src_dir])

            # `cd` first to avoid `csgrep: Argument list too long` error on glob expansion
            dst = f"{results.dbgdir_uni}/cbmc-capture.js"
            cmd = f"""
                  set -ex
                  cd '{src_dir}'
                  for file in pid-*.out; do
                      cbmc-convert-output -a < \"$file\" > \"$file.conv\"
                  done
                  csgrep --mode=json --remove-duplicates pid-*.out.conv > '{dst}'
                  """
            return results.exec_cmd(cmd, shell=True)
        props.post_process_hooks += [filter_hook]
