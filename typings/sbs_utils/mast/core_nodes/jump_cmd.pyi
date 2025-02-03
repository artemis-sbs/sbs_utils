from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class Jump(MastNode):
    """class Jump"""
    def __init__ (self, pop=None, jump=None, jump_name=None, if_exp=None, data=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class JumpRuntimeNode(MastRuntimeNode):
    """class JumpRuntimeNode"""
    def poll (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.jump_cmd.Jump):
        ...
