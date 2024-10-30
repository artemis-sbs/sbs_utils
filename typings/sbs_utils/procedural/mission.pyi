from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def AWAIT (promise: sbs_utils.futures.Promise):
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def mission_find (agent_id):
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
def sub_task_schedule (label, data=None, var=None):
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def task_schedule (label, data=None, var=None):
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
