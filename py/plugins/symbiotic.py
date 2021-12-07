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


SYMBIOTIC_CAPTURE_DIR = "/builddir/symbiotic-capture"

DEFAULT_SYMBIOTIC_TIMEOUT = 30 # TODO


class PluginProps:
    def __init__(self):
        self.description = "A formal verification tool based on instrumentation, program slicing and KLEE."

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
            "--symbiotic-add-flag", action="append", default=[],
            help="append the given flag when invoking symbiotic \
(can be used multiple times)")

        parser.add_argument(
            "--symbiotic-timeout", type=int, default=DEFAULT_SYMBIOTIC_TIMEOUT,
            help="maximal amount of time taken by analysis of a single process [s]")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # make sure symbiotic and gllvm are installed in chroot
        props.add_repos += ["https://download.copr.fedorainfracloud.org/results/@aufover/symbiotic/fedora-$releasever-$basearch/"]
        props.add_repos += ["https://download.copr.fedorainfracloud.org/results/@aufover/gllvm/fedora-$releasever-$basearch/"]
        props.install_pkgs += ["symbiotic", "gllvm"]

        # enable cswrap
        props.enable_cswrap()
        props.cswrap_filters += ["csgrep --mode=json --invert-match --checker CLANG_WARNING --event error"]

        # set dioscc as the default compiler
        # FIXME: this is not 100% reliable
        props.env["CC"]  = "gclang"
        props.env["CXX"] = "gclang++"
        props.rpm_opts += ["--define", "__cc gclang", "--define", "__cxx gclang++", "--define", "__cpp gclang -E"]

        # assert that gllvm is installed properly
        def gllvm_is_working(results, mock):
            return mock.exec_mockbuild_cmd("gsanity-check")
        props.post_depinst_hooks += [gllvm_is_working]

        # nuke default options
        props.rpm_opts += ["--define", "toolchain clang", "--define", "optflags -O0", "--define", "build_ldflags -O0"]

        # record version of the installed "symbiotic" tool
        csmock.common.util.install_default_toolver_hook(props, "symbiotic")

        # hook csexec into the binaries produced in %build
        props.enable_csexec()

        # create directory for symbiotic's results
        def create_cap_dir_hook(results, mock):
            cmd = "mkdir -pv '%s'" % SYMBIOTIC_CAPTURE_DIR
            return mock.exec_mockbuild_cmd(cmd)
        props.post_depinst_hooks += [create_cap_dir_hook]

        # default symbiotic cmd-line
        timeout = args.symbiotic_timeout
        wrap_cmd_list = [
                "--skip-ld-linux",
                "/usr/bin/csexec-symbiotic",
                "-l", SYMBIOTIC_CAPTURE_DIR,
                "-s", f"--prp=memsafety --timeout={timeout} --instrumentation-timeout={timeout} --slicer-timeout={timeout}"]

        # append custom args if specified
        # FIXME: what about single arguments with whitespaces?
        wrap_cmd_list[-1] += " " + " ".join(args.symbiotic_add_flag)

        # FIXME: multiple runs of %check for multiple dynamic analyzers not yet supported
        assert "CSEXEC_WRAP_CMD" not in props.env

        # configure csexec to use symbiotic as the execution wrapper
        wrap_cmd = csmock.common.cflags.serialize_flags(wrap_cmd_list, separator="\\a")
        props.env["CSEXEC_WRAP_CMD"] = wrap_cmd

        # write all compiler flags to the environment
        flags = ['-Wno-unused-command-line-argument',
                 '-Wno-unused-parameter', '-Wno-unknown-attributes',
                 '-Wno-unused-label', '-Wno-unknown-pragmas',
                 '-Wno-unused-command-line-argument',
                 '-fsanitize-address-use-after-scope', '-O0', '-Xclang',
                 '-disable-llvm-passes', '-D__inline=', '-g',
                 '-Wl,--dynamic-linker,/usr/bin/csexec-loader']
        self.flags.append_flags(flags)
        self.flags.remove_flags(['-O1', '-O2', '-O3', '-Os', '-Ofast', '-Og'])
        self.flags.write_to_env(props.env)

        # run %check (disabled by default for static analyzers)
        props.run_check = True

        # pick the captured files when %check is complete
        props.copy_out_files += [SYMBIOTIC_CAPTURE_DIR]

        # transform log files produced by symbiotic into csdiff format
        def filter_hook(results):
            src_dir = results.dbgdir_raw + SYMBIOTIC_CAPTURE_DIR

            # ensure we have permission to read all capture files
            results.exec_cmd(['chmod', '-R', '+r', src_dir])

            # `cd` first to avoid `csgrep: Argument list too long` error on glob expansion
            dst = f"{results.dbgdir_uni}/symbiotic-capture.js"
            cmd = f"cd '{src_dir}' && csgrep --mode=json --remove-duplicates pid-*.conv > {dst}"
            return results.exec_cmd(cmd, shell=True)
        props.post_process_hooks += [filter_hook]
