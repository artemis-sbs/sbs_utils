from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.mast.core_nodes.label import Label
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.futures import PromiseAllAny
from sbs_utils.futures import PromiseWaiter
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Wrap a promise in a non-blocking waiter.
    
    Returns a ``PromiseWaiter`` whose ``done()`` method can be polled each tick
    without suspending the current task.
    
    Args:
        promise (Promise): The promise to wait on.
    
    Returns:
        PromiseWaiter: A waiter that reports completion without blocking."""
def END () -> sbs_utils.mast.pollresults.PollResults:
    """End the current task immediately.
    
    Returns:
        PollResults: ``OK_END`` signal consumed by the task scheduler."""
def LABEL ():
    """Return the currently active label object for the running task.
    
    Returns:
        MastNode | None: The active label, or ``None`` outside a task."""
def LABEL_ALWAYS_IDLE ():
    """Yield ``OK_IDLE`` forever — keeps the current label alive without advancing.
    
    Used as a sentinel label that never completes on its own."""
def awaitable (func):
    ...
def get_shared_variable (key, default=None) -> any:
    """Get the value of a variable from the shared (``Agent.SHARED``) scope.
    
    Args:
        key (str): Variable name.
        default (optional): Value to return when the variable is absent.
            Defaults to None.
    
    Returns:
        any: The variable value, or ``default``."""
def get_variable (key, default=None) -> any:
    """Get the value of a variable from the current task's scope.
    
    Args:
        key (str): Variable name.
        default (optional): Value to return when the variable is absent.
            Defaults to None.
    
    Returns:
        any: The variable value, or ``default``."""
def gui_get_variable (key, defa=None):
    """Get a variable from the client (GUI) task's scope.
    
    Reads from ``FrameContext.client_task``. Comms routes run on the server
    task but still need to read GUI variables from the client task.
    
    Args:
        key (str): Variable name.
        defa (optional): Default if variable is absent. Defaults to None.
    
    Returns:
        any: Variable value, or ``defa``."""
def gui_set_variable (key, value=None):
    """Set a variable in the client (GUI) task's scope.
    
    Writes to ``FrameContext.client_task``. See ``gui_get_variable`` for
    context on why this differs from ``set_variable``.
    
    Args:
        key (str): Variable name.
        value (any, optional): Value to assign. Defaults to None.
    
    Returns:
        any: The value set, or ``value`` if no client task exists."""
def gui_sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """Create a new GUI sub-task and start running at the specified label.
    
    The task is tagged ``end_on_new_gui`` so it is automatically cancelled
    when a new GUI page is presented to the client.
    
    Args:
        label (str | Label): The label to run.
        data (dict, optional): Initial task variables. Defaults to None.
        var (str, optional): Variable name to store the created task. Defaults to None.
    
    Returns:
        MastAsyncTask: The MAST task created."""
def gui_task_jump (label):
    """Redirect the active GUI task to a new label.
    
    Args:
        label (str | Label): The label to jump to."""
def jump (label) -> sbs_utils.mast.pollresults.PollResults:
    """reset the program flow to a label
    
    Args:
        label (str or label): The label to jump to
    
    Returns:
        PollResults: The poll results of the jump. used by the task."""
def labels_get_type (label_type):
    """Return all labels whose type or path starts with the given prefix.
    
    Walks every label in the current story, checking the ``type`` metadata key
    first, then the label ``path`` attribute, then the label name.
    
    Args:
        label_type (str): Prefix to match, e.g. ``"map/"`` or ``"media/"``.
    
    Returns:
        list[MastNode]: Matching label objects."""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
def logger (name: str = None, file: str = None, var: str = None, std_err: bool = False, level: str = None, format=None, file_mode='w') -> None:
    """Configure a named logger with one or more output handlers.
    
    When neither ``file`` nor ``var`` is given, output goes to stderr.
    
    Args:
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        file (str, optional): Path to a log file (relative to mission dir).
            Defaults to None.
        var (str, optional): Shared variable name to receive a ``StringIO``
            stream for in-memory log capture. Defaults to None.
        std_err (bool, optional): Add a stderr handler. Defaults to False
            (forced True when no file or var is supplied).
        level (str, optional): Logging level, e.g. ``"INFO"``, ``"WARNING"``.
            Defaults to None (``DEBUG``).
        format (str, optional): Python log format string. Defaults to None
            (``"%(message)s"``).
        file_mode (str, optional): File open mode — ``'w'`` to overwrite,
            ``'a'`` to append. Defaults to ``'w'``."""
def mast_log (message: str, name: str = None, level: str = None, use_mast_scope=True) -> None:
    """Generate a log message formatted through the current MAST task scope.
    
    Convenience wrapper around ``log`` with ``use_mast_scope=True``.
    
    Args:
        message (str): The message to log. May contain MAST format strings.
        name (str, optional): Logger name. Defaults to None.
        level (str, optional): Logging level string. Defaults to None."""
def metadata_get_value (k, defa=None):
    """Return a metadata value stored on the active label object.
    
    Label metadata is set via MAST inventory calls on the label node itself.
    
    Args:
        k (str): Metadata key to look up.
        defa (optional): Value returned when key is absent. Defaults to None.
    
    Returns:
        any: The metadata value, or ``defa`` if not found."""
def promise_all (*proms):
    """Wait for all promises to resolve.
    
    Args:
        *proms (Promise): Promises to combine.
    
    Returns:
        PromiseAllAny: A promise that resolves when every input promise is done.
    
    Example:
        await promise_all(delay_sim(seconds=5), my_task)"""
def promise_any (*proms):
    """Wait for any one promise to resolve.
    
    Args:
        *proms (Promise): Promises to combine.
    
    Returns:
        PromiseAllAny: A promise that resolves when the first input promise is
            done.
    
    Example:
        await promise_any(delay_sim(seconds=5), abort_signal)"""
def server_get_variable (key, defa=None):
    """Get a variable from the server task's scope.
    
    Args:
        key (str): Variable name.
        defa (optional): Default if variable is absent. Defaults to None.
    
    Returns:
        any: Variable value, or ``defa``."""
def server_set_variable (key, value=None):
    """Set a variable in the server task's scope.
    
    Args:
        key (str): Variable name.
        value (any, optional): Value to assign. Defaults to None.
    
    Returns:
        any: The value set, or ``value`` if no server task exists."""
def set_shared_variable (key, value) -> None:
    """Set a variable in the shared (``Agent.SHARED``) scope.
    
    Shared variables are accessible from any task via ``get_shared_variable``.
    
    Args:
        key (str): Variable name.
        value (any): Value to assign."""
def set_variable (key, value) -> None:
    """Set a variable in the current task's scope.
    
    Args:
        key (str): Variable name.
        value (any): Value to assign."""
def sub_task_all (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Schedule a task for each label and wait until all succeed (or any fails).
    
    Like ``task_all`` but intended for use in sub-task contexts.
    
    Args:
        *args (label): Labels to schedule as tasks.
        data (dict, optional): Keyword argument passed as initial variables to
            every task. Defaults to None.
    
    Returns:
        TaskPromiseAllAny: A promise that resolves when all tasks complete."""
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
def task_all (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Schedule a task for each label and wait until all tasks complete.
    
    Args:
        *args (label): Labels to schedule as parallel tasks.
        data (dict, optional): Keyword argument passed as initial variables to
            every task. Defaults to None.
        sub_tasks (bool, optional): Run as sub-tasks instead of top-level
            tasks. Defaults to False.
    
    Returns:
        TaskPromiseAllAny: A promise that resolves when all tasks complete.
    
    Example:
        await task_all(patrol_alpha, patrol_beta, patrol_gamma)"""
def task_any (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Schedule a task for each label and wait until any one task completes.
    
    Args:
        *args (label): Labels to schedule as parallel tasks.
        data (dict, optional): Keyword argument passed as initial variables to
            every task. Defaults to None.
    
    Returns:
        TaskPromiseAllAny: A promise that resolves when the first task
            completes.
    
    Example:
        await task_any(scan_target, timeout_label)"""
def task_cancel (task: sbs_utils.mast.mastscheduler.MastAsyncTask) -> None:
    """Cancel and end the specified task immediately.
    
    Args:
        task (MastAsyncTask): The task to end."""
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
def task_schedule_client (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """Schedule a new task on the client starting at the given label.
    
    Explicit client-side equivalent of ``task_schedule``.
    
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
        MastAsyncTask: The task created, or None outside a client task context."""
def task_schedule_server (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """Schedule a new task on the server starting at the given label.
    
    Like ``task_schedule`` but always runs under ``FrameContext.server_task``.
    
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
        MastAsyncTask: The task created, or None outside a server task context."""
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
