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
def gui_sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    This is a GUI sub task. It will be marked to end if a new GUI is presented.
    
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
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
def logger (name: str = None, file: str = None, var: str = None, std_err: bool = False, level: str = None, format=None, file_mode='w') -> None:
    """create or retrieve a logger
    
    Args:
        name (str, optional): The name of the logger. Defaults to None.
        file (str, optional): The file to log to. Defaults to None.
        var (str, optional): The name of a string variable to log to. Defaults to None.
        std_err (bool, optional): Include std_err for logger
        level (str, optional): The logger level follow python's
        format: (str, option): The format of the log string following python's logger formats
        file_mode: (str): 'w' = write (default), 'a' append"""
def mast_log (message: str, name: str = None, level: str = None, use_mast_scope=True) -> None:
    """generate a log message using MAST current task
    
    Args:
        message (str): The message to log
        name (str, optional): Name of the logger to log to. Defaults to None.
        level (str, optional): The logging level to use. Defaults to None."""
def metadata_get_value (k, defa=None):
    ...
def promise_all (*proms):
    ...
def promise_any (*proms):
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
def sub_task_all (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when all tasks are completed."""
def sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def task_all (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when all tasks are completed."""
def task_any (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Creates a task for each argument that is a label. Also supports a data named argument to pass the data to all the tasks.
    
    Args:
        args (0..n labels): the labels to schedule.
        data (dict): keyword arg to pass data to the tasks.
    Returns:
        Promise: A promise that is finished when any of the tasks completes."""
def task_cancel (task: sbs_utils.mast.mastscheduler.MastAsyncTask) -> None:
    """ends the specified task
    
    Args:
        task (MastAsyncTask): The task to end"""
def task_schedule (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def task_schedule_client (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    assuring it runs on the client (which should be the same as task_schedule, but this is more explicit)
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def task_schedule_server (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    assuring it runs on the server
    
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
    def end_all (self) -> None:
        ...
    @property
    def is_idle (self) -> bool:
        ...
    def tick_all (self) -> None:
        ...
