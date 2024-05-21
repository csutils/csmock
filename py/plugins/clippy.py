import csmock.common.util

RUN_CLIPPY_CONVERT = "/usr/share/csmock/scripts/convert-clippy.py"
CLIPPY_OUTPUT = "/builddir/clippy-output.txt"
CLIPPY_INSTALL = "/usr/share/csmock/scripts/inject-clippy.sh"

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

        def install_clippy_hook(results, mock):
            return mock.exec_chroot_cmd(CLIPPY_INSTALL)
        props.post_depinst_hooks += [install_clippy_hook]

        props.install_pkgs += ["clippy"]
        props.copy_out_files += [CLIPPY_OUTPUT]

        csmock.common.util.install_default_toolver_hook(props, "clippy")

        def convert_hook(results):
            src = f"{results.dbgdir_raw}{CLIPPY_OUTPUT}"
            dst = f"{results.dbgdir_uni}/clippy-capture.err"
            cmd = f'set -o pipefail; {RUN_CLIPPY_CONVERT} < {src} | csgrep --remove-duplicates > {dst}'
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [convert_hook]
