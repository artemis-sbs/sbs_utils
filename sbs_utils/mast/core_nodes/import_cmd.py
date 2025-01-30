from ..mast import MastNode, mast_node, BLOCK_START
import re


@mast_node()
class Import(MastNode):
    rule = re.compile(r'(from[ \t]+(?P<lib>[\w\.\\\/-]+)[ \t]+)?import\s+(?P<name>[\w\.\\\/-]+)')

    def __init__(self, name, lib=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.name = name
        self.lib = lib


