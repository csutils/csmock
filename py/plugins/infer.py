import csmock.common.util
import re
import os

INFER_RESULTS_FILTER_SCRIPT = "/usr/share/csmock/scripts/filter-infer.py"
INFER_INSTALL_SCRIPT = "/usr/share/csmock/scripts/install-infer.sh"
INFER_RESULTS = "/builddir/infer-results.txt"
INFER_OUT_DIR = "/builddir/infer-out"


class PluginProps:
    def __init__(self):
        self.description = "Static analysis tool for Java/C/C++ code."


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--infer-analyze-add-flag", action="append", default=[],
            help="appends the given flag (except '-o') when invoking 'infer analyze' \
(can be used multiple times)(default flags '--bufferoverrun', '--pulse')")

        parser.add_argument(
            "--infer-archive-path", default="",
            help="use the given archive to install Infer (default is /opt/infer-linux*.tar.xz)")

        csmock.common.util.add_paired_flag(
            parser, "infer-filter",
            help="apply false positive filter (enabled by default)")

        csmock.common.util.add_paired_flag(
            parser, "infer-biabduction-filter",
            help="apply false positive bi-abduction filter (enabled by default)")

        csmock.common.util.add_paired_flag(
            parser, "infer-inferbo-filter",
            help="apply false positive inferbo filter (enabled by default)")

        csmock.common.util.add_paired_flag(
            parser, "infer-uninit-filter",
            help="apply false positive uninit filter (enabled by default)")

        csmock.common.util.add_paired_flag(
            parser, "infer-dead-store-severity",
            help="lower dead store severity (enabled by default)")


    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # python -- for the Infer's reporting module
        # ncurses-compat-libs -- libtinfo.so.5
        # ncurses-libs -- libtinfo.so.6
        props.install_pkgs += ["python", "ncurses-compat-libs", "ncurses-libs"]

        infer_archive_path = ""

        if args.infer_archive_path:
            # use the archive specified with --infer-archive-path
            if os.path.isfile(args.infer_archive_path):
                infer_archive_path = os.path.abspath(args.infer_archive_path)
            else:
                parser.error(f"--infer-archive-path: given path \"{args.infer_archive_path}\" doesn't exist")
        else:
            # search for the archive in /opt
            for file in os.listdir("/opt"):
                if re.search(r"infer-linux.*\.tar\.xz", file):
                    infer_archive_path = "/opt/" + file
            if not infer_archive_path:
                parser.error('The Infer plugin requires an archive with the binary release of Infer. '
                'The archive can be downloaded from https://github.com/facebook/infer/releases. '
                'By default, the plugin looks for the archive in /opt/infer-linux*.tar.xz. '
                'Alternatively, the "--infer-archive-path INFER_ARCHIVE_PATH" option can be '
                'used to specify the path to the archive.')

        props.copy_in_files += [infer_archive_path]

        # install Infer and wrappers for a Infer's capture phase
        install_cmd = f"{INFER_INSTALL_SCRIPT} {infer_archive_path} {INFER_OUT_DIR}"
        def install_infer_hook(results, mock):
            return mock.exec_chroot_cmd(install_cmd)
        props.post_depinst_hooks += [install_infer_hook]

        # run an Infer's analysis phase
        infer_analyze_flags = "--pulse --bufferoverrun"
        if args.infer_analyze_add_flag:
            infer_analyze_flags = csmock.common.cflags.serialize_flags(args.infer_analyze_add_flag, separator=" ")
        run_cmd = f"infer analyze --keep-going {infer_analyze_flags} -o {INFER_OUT_DIR}"
        props.post_build_chroot_cmds += [run_cmd]

        filter_args = []

        if getattr(args, "infer_filter") == False:
            filter_args += ["--only-transform"]

        if getattr(args, "infer_biabduction_filter") == False:
            filter_args += ["--no-biabduction"]

        if getattr(args, "infer_inferbo_filter") == False:
            filter_args += ["--no-inferbo"]

        if getattr(args, "infer_uninit_filter") == False:
            filter_args += ["--no-uninit"]

        if getattr(args, "infer_dead_store_severity") == False:
            filter_args += ["--no-dead-store"]


        filter_args_serialized = csmock.common.cflags.serialize_flags(filter_args, separator=" ")

        # the filter script tries to filter out false positives and transforms results into csdiff compatible format
        filter_cmd = f"python {INFER_RESULTS_FILTER_SCRIPT} {filter_args_serialized} < {INFER_OUT_DIR}/report.json > {INFER_RESULTS}"

        props.post_build_chroot_cmds += [filter_cmd]

        props.copy_out_files += [INFER_RESULTS]

        def filter_hook(results):
            src = results.dbgdir_raw + INFER_RESULTS
            dst = f"{results.dbgdir_uni}/infer-results.err"
            cmd = f"csgrep --quiet {src} > {dst}"
            return results.exec_cmd(cmd, shell=True, echo=True)

        props.post_process_hooks += [filter_hook]
