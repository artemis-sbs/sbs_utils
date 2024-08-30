from sbs_utils.mast.mast import DecoratorLabel
from sbs_utils.mast.mast import DescribableNode
from sbs_utils.mast.mast import MastNode
from sbs_utils.mast.mast import Yield
def STRING_REGEX_NAMED (name):
    ...
class AbortBlock(StateBlock):
    """class AbortBlock"""
    def __init__ (self, is_end=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def parse (lines):
        ...
class CompleteBlock(StateBlock):
    """class CompleteBlock"""
    def __init__ (self, is_end=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def parse (lines):
        ...
class InitBlock(StateBlock):
    """class InitBlock"""
    def __init__ (self, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def parse (lines):
        ...
class MissionLabel(StateMachineLabel):
    """class MissionLabel"""
    def __init__ (self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self):
        ...
    def parse (lines):
        ...
    def test (self, task):
        ...
class ObjectiveBlock(StateBlock):
    """class ObjectiveBlock"""
    def __init__ (self, name=None, display_name=None, q=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def parse (lines):
        ...
class StartBlock(StateBlock):
    """class StartBlock"""
    def __init__ (self, is_end=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def never_indent (self):
        ...
    def parse (lines):
        ...
class StateBlock(DescribableNode):
    """class StateBlock"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class StateMachineLabel(DecoratorLabel):
    """class StateMachineLabel"""
    def __init__ (self, name, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self):
        ...
    def map_cmd (self, key, cmd):
        ...
    def parse (lines):
        ...
    def test (self, task):
        ...
