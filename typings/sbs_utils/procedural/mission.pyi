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
def sub_task_schedule (*args, **kwargs):
    ...
def task_schedule (*args, **kwargs):
    ...
