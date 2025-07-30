from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import Scope
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class OnSignal(MastNode):
    """class OnSignal"""
    def __init__ (self, end=None, signal=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        """cascade the dedent up to the start"""
    def is_indentable (self):
        ...
    def mus_indent (self):
        ...
    def parse (lines):
        ...
class OnSignalRuntimeNode(MastRuntimeNode):
    """class OnSignalRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.on_signal.OnSignal):
        ...
    def poll (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.on_signal.OnSignal):
        ...
