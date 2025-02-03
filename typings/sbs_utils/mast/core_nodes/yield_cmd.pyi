from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import ParseData
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class Yield(MastNode):
    """class Yield"""
    def __init__ (self, res=None, exp=None, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class YieldRuntimeNode(MastRuntimeNode):
    """class YieldRuntimeNode"""
    def poll (self, mast, task, node: sbs_utils.mast.core_nodes.yield_cmd.Yield):
        ...
