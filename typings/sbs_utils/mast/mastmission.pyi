from sbs_utils.mast.mast import DecoratorLabel
from sbs_utils.mast.mast import DescribableNode
from sbs_utils.mast.mast import MastNode
from sbs_utils.mast.mast import Yield
def STRING_REGEX_NAMED (name):
    ...
class Ignore(object):
    """class Ignore"""
class MissionLabel(StateMachineLabel):
    """class MissionLabel"""
    def __init__ (self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self, parent):
        ...
    def parse (lines):
        ...
    def test (self, task):
        ...
class StateLabel(DescribableNode):
    """class StateLabel"""
    def __init__ (self, path, display_name=None, q=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self, parent):
        ...
    def is_indentable (self):
        ...
    def never_indent (self):
        ...
    def parse (lines):
        ...
    def test (self, task):
        ...
class StateMachineLabel(DecoratorLabel):
    """class StateMachineLabel"""
    def __init__ (self, name, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self, parent):
        ...
    def map_cmd (self, key, cmd):
        ...
    def parse (lines):
        ...
    def test (self, task):
        ...
