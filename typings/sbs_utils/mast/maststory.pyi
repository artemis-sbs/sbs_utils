from sbs_utils.mast.mastmission import AbortBlock
from sbs_utils.mast.mastmission import CompleteBlock
from sbs_utils.mast.mastmission import InitBlock
from sbs_utils.mast.mastmission import MissionLabel
from sbs_utils.mast.mastmission import ObjectiveBlock
from sbs_utils.mast.mastmission import StartBlock
from sbs_utils.agent import Agent
from sbs_utils.mast.mast import DecoratorLabel
from sbs_utils.mast.mast import DescribableNode
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import MastNode
def STRING_REGEX_NAMED (name):
    ...
class AppendText(MastNode):
    """class AppendText"""
    def __init__ (self, message, if_exp, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class CommsMessageStart(DescribableNode):
    """class CommsMessageStart"""
    def __init__ (self, mtype, title, q=None, format=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
    def post_dedent (self, compile_info):
        ...
class DefineFormat(MastNode):
    """class DefineFormat"""
    def __init__ (self, name, format, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def is_indentable (self):
        ...
    def is_virtual (self):
        """Virtual nodes are not added to the command stack
        instead the interact with other nodes"""
    def parse (lines):
        ...
    def resolve_colors (c):
        ...
class GuiConsoleDecoratorLabel(DecoratorLabel):
    """class GuiConsoleDecoratorLabel"""
    def __init__ (self, path, display_name, if_exp=None, loc=None, compile_info=None, q=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self):
        ...
    def parse (lines):
        ...
    def test (self, task):
        ...
class GuiTabDecoratorLabel(DecoratorLabel):
    """class GuiTabDecoratorLabel"""
    def __init__ (self, path, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self):
        ...
    def parse (lines):
        ...
    def test (self, task):
        ...
class MapDecoratorLabel(DecoratorLabel):
    """class MapDecoratorLabel"""
    def __init__ (self, path, display_name, if_exp=None, q=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self):
        ...
    def parse (lines):
        ...
class MastStory(Mast):
    """class MastStory"""
class Text(MastNode):
    """class Text"""
    def __init__ (self, message, if_exp, style_name=None, style=None, style_q=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class WeightedText(MastNode):
    """class WeightedText"""
    def __init__ (self, mtype, text, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def is_indentable (self):
        ...
    def is_virtual (self):
        """Virtual nodes are not added to the command stack
        instead the interact with other nodes"""
    def parse (lines):
        ...
