from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import Scope
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class Await(MastNode):
    """waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel"""
    def __init__ (self, until=None, if_exp=None, is_end=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_inline (self, inline_data):
        ...
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class AwaitInlineLabel(MastNode):
    """class AwaitInlineLabel"""
    def __init__ (self, val=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        """cascade the dedent up to the start"""
    def is_indentable (self):
        ...
    def never_indent (self):
        ...
    def parse (lines):
        ...
class AwaitInlineLabelRuntimeNode(MastRuntimeNode):
    """class AwaitInlineLabelRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.await_cmd.AwaitInlineLabel):
        ...
    def leave (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.await_cmd.AwaitInlineLabel):
        ...
    def poll (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.await_cmd.AwaitInlineLabel):
        ...
class AwaitRuntimeNode(MastRuntimeNode):
    """class AwaitRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.await_cmd.Await):
        ...
    def leave (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.await_cmd.Await):
        ...
    def poll (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast.core_nodes.await_cmd.Await):
        ...
