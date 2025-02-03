from sbs_utils.agent import Agent
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class MastAsyncTask(object):
    """class MastAsyncTask"""
class PyCode(MastNode):
    """class PyCode"""
    def __init__ (self, py_cmds=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class PyCodeRuntimeNode(MastRuntimeNode):
    """class PyCodeRuntimeNode"""
    def poll (self, mast, task: sbs_utils.mast.core_nodes.inline_python.MastAsyncTask, node: sbs_utils.mast.core_nodes.inline_python.PyCode):
        ...
