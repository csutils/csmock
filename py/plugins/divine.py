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


DIVINE_CAPTURE_DIR = "/builddir/divine-capture"

DEFAULT_DIVINE_TIMEOUT = 150


class PluginProps:
    def __init__(self):
        self.description = "A formal verification tool based on explicit-state model checking."

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
            "--divine-add-flag", action="append", default=[],
            help="append the given flag when invoking divine (can be used multiple times)")

        parser.add_argument(
            "--divine-timeout", type=int, default=DEFAULT_DIVINE_TIMEOUT,
            help="maximal amount of time taken by analysis of a single process [s]")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # make sure divine and gllvm are installed in chroot
        props.add_repos += ["https://download.copr.fedorainfracloud.org/results/@aufover/divine/fedora-$releasever-$basearch/"]
        props.install_pkgs += ["divine"]

        # enable cswrap
        props.enable_cswrap()
        props.cswrap_filters += ["csgrep --mode=json --invert-match --checker CLANG_WARNING --event error"]

        # set dioscc as the default compiler
        # FIXME: this is not 100% reliable
        props.env["CC"]  = "dioscc"
        props.env["CXX"] = "diosc++"
        props.rpm_opts += ["--define", "__cc dioscc", "--define", "__cxx diosc++", "--define", "__cpp dioscc -E"]

        # nuke default options
        props.rpm_opts += ["--define", "toolchain clang", "--define", "optflags -O0", "--define", "build_ldflags -O0"]

        # record version of the installed "divine" tool
        csmock.common.util.install_default_toolver_hook(props, "divine")

        # hook csexec into the binaries produced in %build
        props.enable_csexec()

        # create directory for divine's results
        def create_cap_dir_hook(results, mock):
            cmd = "mkdir -pv '%s'" % DIVINE_CAPTURE_DIR
            return mock.exec_mockbuild_cmd(cmd)
        props.post_depinst_hooks += [create_cap_dir_hook]

        # default divine cmd-line
        wrap_cmd_list = [
                "--skip-ld-linux",
                "csexec-divine",
                "-l", DIVINE_CAPTURE_DIR,
                "-d", "check --max-time %d" % args.divine_timeout]

        # append custom args if specified
        # FIXME: what about single arguments with whitespaces?
        wrap_cmd_list[-1] += " " + " ".join(args.divine_add_flag)

        # FIXME: multiple runs of %check for multiple dynamic analyzers not yet supported
        assert "CSEXEC_WRAP_CMD" not in props.env

        # configure csexec to use divine as the execution wrapper
        wrap_cmd = csmock.common.cflags.serialize_flags(wrap_cmd_list, separator="\\a")
        props.env["CSEXEC_WRAP_CMD"] = wrap_cmd

        # write all compiler flags to the environment
        self.flags.append_flags(['-Wno-unknown-warning-option', '-O0', '-g', '-Wl,--dynamic-linker,/usr/bin/csexec-loader'])
        self.flags.remove_flags(['-O1', '-O2', '-O3', '-Os', '-Ofast', '-Og'])
        self.flags.write_to_env(props.env)

        # run %check (disabled by default for static analyzers)
        props.run_check = True

        # pick the captured files when %check is complete
        props.copy_out_files += [DIVINE_CAPTURE_DIR]

        # transform log files produced by divine into csdiff format
        def filter_hook(results):
            src_dir = results.dbgdir_raw + DIVINE_CAPTURE_DIR
            dst = "%s/divine-capture.js" % results.dbgdir_uni
            cmd = "csgrep --mode=json --remove-duplicates '%s'/pid-*.conv > '%s'" \
                  % (src_dir, dst)
            return results.exec_cmd(cmd, shell=True)
        props.post_process_hooks += [filter_hook]
