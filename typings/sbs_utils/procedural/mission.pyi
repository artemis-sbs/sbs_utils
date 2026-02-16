from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def mission_find (agent_id):
    """Currently unused."""
def mission_run (label, data=None):
    """Run a mission label.
    Args:
        label (str | Label)"""
def mission_runner (label=None, data=None):
    """Runs a mission this runs the same task multiple times. If the label is None, runs the currently running mission label.
    
    Args:
        label (str | Label, optional): The mission label to run. Default is None.
        data (dict, optional): Data to pass to the mission task. Default is None.
    
    Yields:
        PollResults: Success or Failure"""
def sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def task_schedule (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
