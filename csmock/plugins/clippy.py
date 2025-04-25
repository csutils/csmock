import os

from csmock.common.util import write_toolver_from_rpmlist

RUN_CLIPPY_CONVERT = "/usr/share/csmock/scripts/convert-clippy.py"
CLIPPY_OUTPUT = "/builddir/clippy-output.txt"
CLIPPY_INJECT_SCRIPT = "/usr/share/csmock/scripts/inject-clippy.sh"

class PluginProps:
    def __init__(self):
        self.description = "Rust source code analyzer which looks for programming errors."


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        return

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # install `clippy` only if the package is available in the build repos
        props.install_opt_pkgs += ["clippy"]

        def inject_clippy_hook(results, mock):
            ec = write_toolver_from_rpmlist(results, mock, "clippy", "clippy")
            if 0 != ec:
                # a warning has already been emitted
                return 0

            # clippy was found in the buildroot -> instrument the build
            props.copy_out_files += [CLIPPY_OUTPUT]
            return mock.exec_chroot_cmd(CLIPPY_INJECT_SCRIPT)

        props.post_depinst_hooks += [inject_clippy_hook]

        def convert_hook(results):
            src = f"{results.dbgdir_raw}{CLIPPY_OUTPUT}"
            if not os.path.exists(src):
                # if `cargo build` was not executed during the scan, there are no results to process
                return 0

            dst = f"{results.dbgdir_uni}/clippy-capture.err"
            cmd = f'set -o pipefail; {RUN_CLIPPY_CONVERT} < {src} | csgrep --remove-duplicates > {dst}'
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [convert_hook]
