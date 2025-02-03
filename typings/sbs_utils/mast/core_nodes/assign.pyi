from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import Scope
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class Assign(MastNode):
    """class Assign"""
    def __init__ (self, is_default, scope, lhs, oper, exp, a_wait=None, quote=None, py=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class AssignRuntimeNode(MastRuntimeNode):
    """class AssignRuntimeNode"""
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self, mast, task: sbs_utils.mast.core_nodes.assign.MastAsyncTask, node: sbs_utils.mast.core_nodes.assign.Assign):
        ...
class MastAsyncTask(object):
    """class MastAsyncTask"""
