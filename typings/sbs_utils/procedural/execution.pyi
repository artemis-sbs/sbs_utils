from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.futures import PromiseAllAny
from sbs_utils.futures import PromiseWaiter
def AWAIT (promise: sbs_utils.futures.Promise):
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def END ():
    """End the current task
    Returns:
        PollResults: The poll results of the jump. used by the task."""
def get_shared_variable (key, default=None):
    """get the value of a variable at shared scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        default (optional): What to return if the variable doesn't exist. Defaults to None.
    
    Returns:
        any: The value of the variable, or default value"""
def get_variable (key, default=None):
    """get the value of a variable at task scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        default (optional): What to return if the variable doesn't exist. Defaults to None.
    
    Returns:
        any: The value of the variable, or default value"""
def jump (label):
    """reset the program flow to a label
    
    Args:
        label (str or label): The label to jump to
    
    Returns:
        PollResults: The poll results of the jump. used by the task."""
def log (message, name=None, level=None):
    """generate a log message
    
    Args:
        message (str): The message to log
        name (str, optional): Name of the logger to log to. Defaults to None.
        level (str, optional): The logging level to use. Defaults to None."""
def logger (name=None, file=None, var=None, std_err=False):
    """create or retreive a looger
    
    Args:
        name (str, optional): The name of the logger. Defaults to None.
        file (str, optional): The file to log to. Defaults to None.
        var (str, optional): The name of a string variable to log to. Defaults to None."""
def set_shared_variable (key, value):
    """set the value of a variable at shared scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        value (any): The value to set the variable to"""
def set_variable (key, value):
    """set the value of a variable at task scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        value (any): The value to set the variable to"""
def sub_task_all (*args, **kwargs):
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when all tasks are completed."""
def sub_task_schedule (label, data=None, var=None):
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def task_all (*args, **kwargs):
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when all tasks are completed."""
def task_any (*args, **kwargs):
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when any of the tasks completes."""
def task_cancel (task):
    """ends the specified task
    
    Args:
        task (MastAsyncTAsk): The task to end"""
def task_schedule (label, data=None, var=None):
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
class TaskPromiseAllAny(PromiseAllAny):
    """class TaskPromiseAllAny"""
    def __init__ (self, proms, all) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def end_all (self):
        ...
    @property
    def is_idle (self):
        ...
