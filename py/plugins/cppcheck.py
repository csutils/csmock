import os

class PluginProps:
    def __init__(self):
        self.pass_priority = 0x20

class Plugin:
    def __init__(self):
        self.enabled = False
        self.use_host_cppcheck = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument("--use-host-cppcheck", action="store_true",
                help="use host's Cppcheck instead of the one in chroot \
(automatically enables the Cppcheck plug-in)")

    def handle_args(self, args, props):
        self.use_host_cppcheck = args.use_host_cppcheck
        if self.use_host_cppcheck:
            self.enable()

        if not self.enabled:
            return

        props.enable_cswrap()
        props.cswrap_filters += ["csgrep --invert-match \
--checker CPPCHECK_WARNING \
--event 'preprocessorErrorDirective|syntaxError'"]

        # FIXME: /usr/lib64 is arch-specific
        props.path = ["/usr/lib64/cscppc"] + props.path
        props.copy_in_files += \
                ["/usr/bin/cscppc", "/usr/lib64/cscppc", "/usr/share/cscppc"]

        if self.use_host_cppcheck:
            # install only tinyxml2
            props.install_pkgs += ["tinyxml2"]

            # copy cppcheck's binaries into the chroot
            props.copy_in_files += ["/usr/bin/cppcheck"]
            if os.path.isdir("/usr/share/cppcheck"):
                props.copy_in_files += ["/usr/share/cppcheck"]
        else:
            # install cppcheck into the chroot
            props.install_pkgs += ["cppcheck"]
