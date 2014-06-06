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

        # FIXME: /usr/lib64 is arch-specific
        props.copy_in_files += ["/usr/bin/cswrap", "/usr/lib64/cswrap"]
        props.path = ["/usr/lib64/cswrap"] + props.path
        props.env["CSWRAP_CAP_FILE"] = "/builddir/cswrap-capture.err"
        props.env["CSWRAP_TIMEOUT"] = "300"
