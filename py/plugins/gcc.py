class PluginProps:
    def __init__(self):
        self.pass_priority = 0x10

class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def handle_args(self, args, props):
        # TODO: handle args
        if not self.enabled:
            return

        props.enable_cswrap()
        props.cswrap_filters += \
            ["csgrep --invert-match --checker COMPILER_WARNING --event error"]
