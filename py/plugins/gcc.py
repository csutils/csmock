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
