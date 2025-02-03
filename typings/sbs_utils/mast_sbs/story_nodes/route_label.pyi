from sbs_utils.mast.core_nodes.decorator_label import DecoratorLabel
from sbs_utils.mast.core_nodes.inline_function import FuncCommand
from sbs_utils.mast.core_nodes.yield_cmd import Yield
def mast_node (append=True):
    ...
class RouteDecoratorLabel(DecoratorLabel):
    """class RouteDecoratorLabel"""
    def __init__ (self, path, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self, p):
        ...
    def generate_label_begin_cmds (self, compile_info=None):
        ...
    def generate_label_end_cmds (self, compile_info=None):
        ...
    def parse (lines):
        ...
