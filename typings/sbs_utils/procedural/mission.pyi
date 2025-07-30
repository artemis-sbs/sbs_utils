from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
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
def sub_task_schedule (*args, **kwargs):
    ...
def task_schedule (*args, **kwargs):
    ...
