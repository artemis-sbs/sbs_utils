from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class InlineLabel(MastNode):
    """class InlineLabel"""
    def __init__ (self, name, m=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def never_indent (self):
        ...
    def parse (lines):
        ...
class InlineLabelRuntimeNode(MastRuntimeNode):
    """class InlineLabelRuntimeNode"""
    def poll (self, mast, task, node: sbs_utils.mast.core_nodes.inline_label.InlineLabel):
        ...
