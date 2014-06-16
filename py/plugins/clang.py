import os

class PluginProps:
    def __init__(self):
        self.pass_priority = 0x30

class Plugin:
    def __init__(self):
        self.enabled = False
        self.use_host_cppcheck = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        # TODO: introduce options to enable/disable checkers
        pass

    def handle_args(self, args, props):
        if not self.enabled:
            return

        props.enable_cswrap()
        props.cswrap_filters += \
                ["csgrep --invert-match --checker CLANG_WARNING --event error"]

        props.install_pkgs += ["clang-analyzer", "imake"]

        props.copy_in_files += ["/usr/share/csmock/scripts/fixups-clang.sh"]

        props.build_cmd_wrappers += ["scan-build -plist %s"]
