from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.core_nodes.label import Label
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.futures import PromiseAllAny
from sbs_utils.futures import PromiseWaiter
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def END () -> sbs_utils.mast.pollresults.PollResults:
    """End the current task
    Returns:
        PollResults: The poll results of the jump. used by the task."""
def LABEL ():
    ...
def awaitable (func):
    ...
def get_shared_variable (key, default=None) -> any:
    """get the value of a variable at shared scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        default (optional): What to return if the variable doesn't exist. Defaults to None.
    
    Returns:
        any: The value of the variable, or default value"""
def get_variable (key, default=None) -> any:
    """get the value of a variable at task scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        default (optional): What to return if the variable doesn't exist. Defaults to None.
    
    Returns:
        any: The value of the variable, or default value"""
def gui_get_variable (key, defa=None):
    ...
def gui_set_variable (key, value=None):
    ...
def gui_sub_task_schedule (*args, **kwargs):
    ...
def gui_task_jump (label):
    """Will redirect the gui_task to a new label
    
    Args:
        label (str or label): The label to run"""
def jump (label) -> sbs_utils.mast.pollresults.PollResults:
    """reset the program flow to a label
    
    Args:
        label (str or label): The label to jump to
    
    Returns:
        PollResults: The poll results of the jump. used by the task."""
def labels_get_type (label_type):
    ...
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """generate a log message
    
        note: MAST exposes mast_log as log so it by default uses MAST scope
    Args:
        message (str): The message to log
        name (str, optional): Name of the logger to log to. Defaults to None.
        level (str, optional): The logging level to use. Defaults to None."""
def logger (name: str = None, file: str = None, var: str = None, std_err: bool = False) -> None:
    """create or retreive a looger
    
    Args:
        name (str, optional): The name of the logger. Defaults to None.
        file (str, optional): The file to log to. Defaults to None.
        var (str, optional): The name of a string variable to log to. Defaults to None."""
def mast_log (message: str, name: str = None, level: str = None, use_mast_scope=True) -> None:
    """generate a log message using MAST current task
    
    Args:
        message (str): The message to log
        name (str, optional): Name of the logger to log to. Defaults to None.
        level (str, optional): The logging level to use. Defaults to None."""
def metadata_get_value (k, defa=None):
    ...
def promise_all (*args, **kwargs):
    ...
def promise_any (*args, **kwargs):
    ...
def server_get_variable (key, defa=None):
    ...
def server_set_variable (key, value=None):
    ...
def set_shared_variable (key, value) -> any:
    """set the value of a variable at shared scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        value (any): The value to set the variable to"""
def set_variable (key, value) -> None:
    """set the value of a variable at task scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        value (any): The value to set the variable to"""
def sub_task_all (*args, **kwargs):
    ...
def sub_task_schedule (*args, **kwargs):
    ...
def task_all (*args, **kwargs):
    ...
def task_any (*args, **kwargs):
    ...
def task_cancel (task: sbs_utils.mast.mastscheduler.MastAsyncTask) -> None:
    """ends the specified task
    
    Args:
        task (MastAsyncTask): The task to end"""
def task_schedule (*args, **kwargs):
    ...
def task_schedule_client (*args, **kwargs):
    ...
def task_schedule_server (*args, **kwargs):
    ...
class TaskPromiseAllAny(PromiseAllAny):
    """class TaskPromiseAllAny"""
    def __init__ (self, proms, all) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def end_all (self) -> None:
        ...
    @property
    def is_idle (self) -> bool:
        ...
    def tick_all (self) -> None:
        ...
