from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import ParseData
from sbs_utils.mast.mast_node import Scope
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class WithEnd(MastNode):
    """LoopEnd is a node that is injected to allow loops to know where the end is"""
    def __init__ (self, start=None, name=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class WithEndRuntimeNode(MastRuntimeNode):
    """class WithEndRuntimeNode"""
    def poll (self, mast, task, node: sbs_utils.mast.core_nodes.with_cmd.WithEnd):
        ...
class WithStart(MastNode):
    """class WithStart"""
    def __init__ (self, obj=None, name=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, _, compile_info):
        ...
    def is_indentable (self):
        ...
    def must_indent (self):
        ...
    def parse (lines):
        ...
class WithStartRuntimeNode(MastRuntimeNode):
    """class WithStartRuntimeNode"""
    def poll (self, mast, task, node: sbs_utils.mast.core_nodes.with_cmd.WithStart):
        ...
