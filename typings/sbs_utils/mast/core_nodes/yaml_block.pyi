from sbs_utils.mast.mast_node import MastNode
def mast_node (append=True):
    ...
class YamlBlock(MastNode):
    """class YamlBlock"""
    def __init__ (self, tag=None, data=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def is_indentable (self):
        ...
    def is_virtual (self):
        """Virtual nodes are not added to the command stack
        instead the interact with other nodes"""
    def parse (lines):
        ...
