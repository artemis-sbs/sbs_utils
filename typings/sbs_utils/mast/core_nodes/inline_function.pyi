from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class FuncCommand(MastNode):
    """class FuncCommand"""
    def __init__ (self, is_await=None, py_cmds=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class FuncCommandRuntimeNode(MastRuntimeNode):
    """class FuncCommandRuntimeNode"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def enter (self, mast, task: sbs_utils.mast.core_nodes.inline_function.MastAsyncTask, node: sbs_utils.mast.core_nodes.inline_function.FuncCommand):
        ...
    def poll (self, mast, task: sbs_utils.mast.core_nodes.inline_function.MastAsyncTask, node: sbs_utils.mast.core_nodes.inline_function.FuncCommand):
        ...
class MastAsyncTask(object):
    """class MastAsyncTask"""
