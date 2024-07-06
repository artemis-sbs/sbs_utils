from sbs_utils.mast.mast import DecoratorLabel
from sbs_utils.mast.mast import DescribableNode
from sbs_utils.mast.mast import MastNode
from sbs_utils.mast.mast import Yield
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def AWAIT (promise: sbs_utils.futures.Promise):
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def STRING_REGEX_NAMED (name):
    ...
def mission_run (label, data=None):
    ...
def mission_runner (label=None, data=None):
    """Runs a mission this runs the same task multiple times
    
    Args:
        label (_type_): a Mission Label
        data (_type_, optional): _Data to pass to the mission task. Defaults to None.
    
    Yields:
        PollResults: Sucess or Failure"""
def task_schedule (label, data=None, var=None):
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
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
