from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Wrap a promise in a non-blocking waiter.
    
    Returns a ``PromiseWaiter`` whose ``done()`` method can be polled each tick
    without suspending the current task.
    
    Args:
        promise (Promise): The promise to wait on.
    
    Returns:
        PromiseWaiter: A waiter that reports completion without blocking."""
def mission_find (agent_id):
    """Find a mission by agent ID — currently unused and always returns ``None``.
    
    Args:
        agent_id (int): Agent ID to search for."""
def mission_run (label, data=None):
    """Schedule a mission label to run as a new task.
    
    Spawns a task running ``mission_runner`` which drives the mission label
    through its full ``init`` / ``start`` / ``objective`` / ``complete``
    lifecycle.
    
    Args:
        label (str | Label): The mission label to execute.
        data (dict, optional): Variables to pass into the mission. Defaults to
            None.
    
    Returns:
        MastAsyncTask: The scheduled task."""
def mission_runner (label=None, data=None):
    """Generator that drives a structured mission label through its lifecycle.
    
    Executes the ``init``, ``start``, ``abort``, ``objective``, and
    ``complete`` sub-blocks of a mission label in order, yielding
    ``PollResults`` at each step. If ``label`` is ``None``, reads the label
    and data from the current task's variables (used when spawned by
    ``mission_run``).
    
    Args:
        label (str | Label, optional): The mission label to run. Defaults to
            ``None`` (reads from the current task).
        data (dict, optional): Variables to pass into the mission sub-task.
            Defaults to None.
    
    Yields:
        PollResults: ``OK_RUN_AGAIN`` while running, ``OK_END`` on completion
            or abort."""
def sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """Schedule a sub-task under the current task starting at the given label.
    
    Sub-tasks share lifecycle with the parent task.
    
    Args:
        label (str | Label): The label to start the sub-task at.
        data (dict, optional): Initial sub-task variables. Defaults to None.
        var (str, optional): Variable name to store the created sub-task.
            Defaults to None.
    
    Returns:
        MastAsyncTask: The sub-task created, or None outside a task context."""
def task_schedule (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """Schedule a new task starting at the given label.
    
    Args:
        label (str | Label): The label to start the task at.
        data (dict, optional): Initial task variables. Defaults to None.
        var (str, optional): Variable name to store the created task. Defaults
            to None.
        defer (bool, optional): Defer first tick to the next frame. Defaults to
            False.
        inherit (bool, optional): Inherit parent task variables. Defaults to
            True.
        unscheduled (bool, optional): Create without scheduling immediately.
            Defaults to False.
    
    Returns:
        MastAsyncTask: The task created, or None outside a task context."""
