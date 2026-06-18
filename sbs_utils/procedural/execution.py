from ..helpers import FrameContext, FrameContextOverride
import logging as logging
from ..agent import Agent
from io import StringIO
from ..futures import Promise, PromiseAllAny, PromiseWaiter, awaitable
from ..mast.pollresults import PollResults
from .. import fs
from ..mast.core_nodes.label import Label
from ..mast.mastscheduler import MastAsyncTask

def jump(label) -> PollResults:
    """reset the program flow to a label

    Args:
        label (str or label): The label to jump to

    Returns:
        PollResults: The poll results of the jump. used by the task.
    """    
    task = FrameContext.task

    if task is not None:
        task.jump(label)
        task.tick_in_context()
    return PollResults.OK_JUMP

def END() -> PollResults:
    """End the current task immediately.

    Returns:
        PollResults: ``OK_END`` signal consumed by the task scheduler.
    """
    task = FrameContext.task

    if task is not None:
        return task.end()
    return PollResults.OK_END


def LABEL():
    """Return the currently active label object for the running task.

    Returns:
        MastNode | None: The active label, or ``None`` outside a task.
    """
    task = FrameContext.task
    if task is not None:
        return task.active_label_object
    return None

def LABEL_ALWAYS_IDLE():
    """Yield ``OK_IDLE`` forever — keeps the current label alive without advancing.

    Used as a sentinel label that never completes on its own.
    """
    from ..mast.pollresults import PollResults
    while True:
        yield PollResults.OK_IDLE

def metadata_get_value(k, defa=None):
    """Return a metadata value stored on the active label object.

    Label metadata is set via MAST inventory calls on the label node itself.

    Args:
        k (str): Metadata key to look up.
        defa (optional): Value returned when key is absent. Defaults to None.

    Returns:
        any: The metadata value, or ``defa`` if not found.
    """
    label = LABEL()
    if label is None:
        return defa
    return label.get_inventory_value(k, defa)


def mast_log(message: str, name: str=None, level: str=None, use_mast_scope=True) -> None:
    """Generate a log message formatted through the current MAST task scope.

    Convenience wrapper around ``log`` with ``use_mast_scope=True``.

    Args:
        message (str): The message to log. May contain MAST format strings.
        name (str, optional): Logger name. Defaults to None.
        level (str, optional): Logging level string. Defaults to None.
    """
    log(message, name, level, use_mast_scope)


def log(message: str, name: str=None, level: str=None, use_mast_scope=False) -> None:
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
            MAST task. Defaults to False.
    """
    if use_mast_scope:
        task = FrameContext.task
        if task is not None:
            message = task.compile_and_format_string(message)

    if name is None:
        name = "__base_logger__"
    _logger = logging.getLogger(name)

    if isinstance(level, str):
        level = level.upper()
        level = logging.getLevelNamesMapping.get(level)
    if level is None:
        level = logging.DEBUG
    _logger.log(level, message)

def logger(name: str=None, file: str=None, var: str=None, std_err:bool=False, level: str=None, format=None, file_mode='w') -> None:
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
            ``'a'`` to append. Defaults to ``'w'``.
    """
    if name is None:
        # name = "__base_logger__"
        _logger = logging.getLogger("__base_logger__")
    else:
        _logger = logging.getLogger(name)

    if isinstance(level, str):
        level = level.upper()
        level = logging.getLevelNamesMapping.get(level)
    if level is None:
        level = logging.DEBUG

    _logger.setLevel(level)
    if format is None:
        format = "%(message)s"

    force_std = file is None and var is None
    std_err = std_err or force_std
    if std_err:    
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(format))
        handler.setLevel(level)
        _logger.addHandler(handler)


    if var is not None:
        streamer = StringIO()
        handler = logging.StreamHandler(stream=streamer)
        handler.setFormatter(logging.Formatter(format))
        handler.setLevel(level)
        _logger.addHandler(handler)
        #mast.vars[node.var] = streamer
        Agent.SHARED.set_inventory_value(var, streamer)

    task = FrameContext.task
    if file is not None and task is not None:
        file = task.format_string(file)
        file = fs.get_mission_dir_filename(file)
        handler = logging.FileHandler(file,mode=file_mode)
        handler.setFormatter(logging.Formatter(format))
        handler.setLevel(level)
        _logger.addHandler(handler)


@awaitable
def task_schedule(label: str | Label, data=None, var:str=None, defer=False, inherit=True, unscheduled=False) -> "MastAsyncTask":
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
        MastAsyncTask: The task created, or None outside a task context.
    """
    task = FrameContext.task
    if task is not None:
        t = task.start_task(label, data, var, defer, inherit, unscheduled)
        return t
    return None

@awaitable
def task_schedule_server(label: str | Label, data=None, var:str=None, defer=False, inherit=True, unscheduled=False) -> "MastAsyncTask":
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
        MastAsyncTask: The task created, or None outside a server task context.
    """
    task = FrameContext.server_task
    if task is not None:
        t = task.start_task(label, data, var, defer, inherit, unscheduled)
        return t
    return None

@awaitable
def task_schedule_client(label: str | Label, data=None, var:str=None, defer=False, inherit=True, unscheduled=False) -> "MastAsyncTask":
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
        MastAsyncTask: The task created, or None outside a client task context.
    """
    task = FrameContext.client_task
    if task is not None:
        t = task.start_task(label, data, var, defer, inherit, unscheduled)
        return t
    return None



@awaitable
def sub_task_schedule(label, data=None, var=None) -> "MastAsyncTask":
    """Schedule a sub-task under the current task starting at the given label.

    Sub-tasks share lifecycle with the parent task.

    Args:
        label (str | Label): The label to start the sub-task at.
        data (dict, optional): Initial sub-task variables. Defaults to None.
        var (str, optional): Variable name to store the created sub-task.
            Defaults to None.

    Returns:
        MastAsyncTask: The sub-task created, or None outside a task context.
    """
    task = FrameContext.task
    if task is not None:
        t = task.start_sub_task(label, data, var)
        return t
    return None

@awaitable
def gui_sub_task_schedule(label, data=None, var=None) -> "MastAsyncTask":
    """Create a new GUI sub-task and start running at the specified label.

    The task is tagged ``end_on_new_gui`` so it is automatically cancelled
    when a new GUI page is presented to the client.

    Args:
        label (str | Label): The label to run.
        data (dict, optional): Initial task variables. Defaults to None.
        var (str, optional): Variable name to store the created task. Defaults to None.

    Returns:
        MastAsyncTask: The MAST task created.
    """
    gui_task = FrameContext.client_task
    task = FrameContext.task

        # 
    # Look for sub label
    #
    active_cmd = 0
    if isinstance(label, str):
        label_obj = task.active_label_object 
        if label_obj is not None:
            sub_label = label_obj.labels.get(label)
            if sub_label is not None:
                label = label_obj
                active_cmd = sub_label.loc
    
    if task is not None:
        t = gui_task.start_sub_task(label, data, var, False, active_cmd)
        t.add_role("end_on_new_gui")
        return t
    return None


def task_cancel(task:MastAsyncTask) -> None:
    """Cancel and end the specified task immediately.

    Args:
        task (MastAsyncTask): The task to end.
    """
    task.cancel()

class TaskPromiseAllAny(PromiseAllAny):
    def __init__(self, proms, all) -> None:
        super().__init__(proms, all)

    @property
    def is_idle(self) -> bool:
        for t in self.promises:
            if t is None:
                continue
            if t.tick_result != PollResults.OK_IDLE:
                return False
        return True

    def end_all(self) -> None:
        for t in self.promises:
            if t is None:
                continue
            t.cancel()

    def tick_all(self) -> None:
        for t in self.promises:
            if t is None:
                continue
            if t.done():
                continue
            t.tick_in_context()



#
# Args are labels or task
#
# Doesn't return until all success, or any fail
#
@awaitable
def task_all(*args, **kwargs) -> TaskPromiseAllAny:
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
        await task_all(patrol_alpha, patrol_beta, patrol_gamma)
    """
    if FrameContext.task is None:
        return
    data = None
    sub_tasks = False
    if kwargs is not None:
        data = kwargs.get("data", None)
        sub_tasks = kwargs.get("sub_tasks", False)
    tasks = []
    for label in args:
        if not sub_tasks:
            t = FrameContext.task.start_task(label, data)
        else:
            t = FrameContext.task.start_sub_task(label, data)
        tasks.append(t)
    return TaskPromiseAllAny(tasks, True)

#
# Args are labels or task
#
# Doesn't return until all success, or any fail
#
@awaitable
def sub_task_all(*args, **kwargs) -> TaskPromiseAllAny:
    """Schedule a task for each label and wait until all succeed (or any fails).

    Like ``task_all`` but intended for use in sub-task contexts.

    Args:
        *args (label): Labels to schedule as tasks.
        data (dict, optional): Keyword argument passed as initial variables to
            every task. Defaults to None.

    Returns:
        TaskPromiseAllAny: A promise that resolves when all tasks complete.
    """
    if FrameContext.task is None:
        return
    data = None
    if kwargs is not None:
        data = kwargs.get("data", None)
    tasks = []
    for label in args:
        t = FrameContext.task.start_task(label, data)
        tasks.append(t)
    return TaskPromiseAllAny(tasks, True)





#
# Args are labels or task
#
# Doesn't return until any success, or all fail
#
@awaitable
def task_any(*args, **kwargs) -> TaskPromiseAllAny:
    """Schedule a task for each label and wait until any one task completes.

    Args:
        *args (label): Labels to schedule as parallel tasks.
        data (dict, optional): Keyword argument passed as initial variables to
            every task. Defaults to None.

    Returns:
        TaskPromiseAllAny: A promise that resolves when the first task
            completes.

    Example:
        await task_any(scan_target, timeout_label)
    """
    if FrameContext.task is None:
        return
    data = None
    if kwargs is not None:
        data = kwargs.get("data", None)
    tasks = []
    for label in args:
        t = FrameContext.task.start_task(label, data)
        tasks.append(t)
    return TaskPromiseAllAny(tasks, False)



def set_variable(key, value) -> None:
    """Set a variable in the current task's scope.

    Args:
        key (str): Variable name.
        value (any): Value to assign.
    """
 
    if FrameContext.task is None:
        return
    FrameContext.task.set_variable(key,value)

def get_variable(key, default=None) -> any:
    """Get the value of a variable from the current task's scope.

    Args:
        key (str): Variable name.
        default (optional): Value to return when the variable is absent.
            Defaults to None.

    Returns:
        any: The variable value, or ``default``.
    """
    if FrameContext.task is None:
        print("NOT HERE")
        return None
    return FrameContext.task.get_variable(key,default)


def get_shared_variable(key, default=None) -> any:
    """Get the value of a variable from the shared (``Agent.SHARED``) scope.

    Args:
        key (str): Variable name.
        default (optional): Value to return when the variable is absent.
            Defaults to None.

    Returns:
        any: The variable value, or ``default``.
    """
    return Agent.SHARED.get_inventory_value(key, default)
    

def set_shared_variable(key, value) -> None:
    """Set a variable in the shared (``Agent.SHARED``) scope.

    Shared variables are accessible from any task via ``get_shared_variable``.

    Args:
        key (str): Variable name.
        value (any): Value to assign.
    """
    Agent.SHARED.set_inventory_value(key, value)

def gui_get_variable(key, defa=None):
    """Get a variable from the client (GUI) task's scope.

    Reads from ``FrameContext.client_task``. Comms routes run on the server
    task but still need to read GUI variables from the client task.

    Args:
        key (str): Variable name.
        defa (optional): Default if variable is absent. Defaults to None.

    Returns:
        any: Variable value, or ``defa``.
    """
    #
    # This is confusing because of COMMS
    # Comms runs on the sever task, but the GUI needs
    # to be the client for the comms operations
    # So COMMS is setting the page to the client
    # and the server task is the task
    #
    gui_task = FrameContext.client_task
    
    if gui_task is not None:
        v = gui_task.get_variable(key, defa)
        return v
    
    return defa

def gui_set_variable(key, value=None):
    """Set a variable in the client (GUI) task's scope.

    Writes to ``FrameContext.client_task``. See ``gui_get_variable`` for
    context on why this differs from ``set_variable``.

    Args:
        key (str): Variable name.
        value (any, optional): Value to assign. Defaults to None.

    Returns:
        any: The value set, or ``value`` if no client task exists.
    """
    #
    # This is confusing because of COMMS
    # Comms runs on the sever task, but the GUI needs
    # to be the client for the comms operations
    # So COMMS is setting the page to the client
    # and the server task is the task
    #
    gui_task = FrameContext.client_task
    if gui_task is not None:
        return gui_task.set_variable(key, value)
    return value


def server_get_variable(key, defa=None):
    """Get a variable from the server task's scope.

    Args:
        key (str): Variable name.
        defa (optional): Default if variable is absent. Defaults to None.

    Returns:
        any: Variable value, or ``defa``.
    """
    server_task = FrameContext.server_task
    
    if server_task is not None:
        v = server_task.get_variable(key, defa)
        return v
    
    return defa

def server_set_variable(key, value=None):
    """Set a variable in the server task's scope.

    Args:
        key (str): Variable name.
        value (any, optional): Value to assign. Defaults to None.

    Returns:
        any: The value set, or ``value`` if no server task exists.
    """
    server_task = FrameContext.server_task
    if server_task is not None:
        return server_task.set_variable(key, value)
    return value


def AWAIT(promise: Promise) -> PromiseWaiter:
    """Wrap a promise in a non-blocking waiter.

    Returns a ``PromiseWaiter`` whose ``done()`` method can be polled each tick
    without suspending the current task.

    Args:
        promise (Promise): The promise to wait on.

    Returns:
        PromiseWaiter: A waiter that reports completion without blocking.
    """
    return PromiseWaiter(promise)
    
def labels_get_type(label_type):
    """Return all labels whose type or path starts with the given prefix.

    Walks every label in the current story, checking the ``type`` metadata key
    first, then the label ``path`` attribute, then the label name.

    Args:
        label_type (str): Prefix to match, e.g. ``"map/"`` or ``"media/"``.

    Returns:
        list[MastNode]: Matching label objects.
    """
    ret = []
    page = FrameContext.page
    if page is None or label_type is None:
        return []
    #
    # Walk all labels looking for map Labels
    #
    all_labels = page.story.labels
    for l in all_labels:
        label = all_labels.get(l)
        if label is None:
            continue # Bad Label??
        test = label.get_inventory_value("type")
        if test is None and hasattr(label, "path"):
            test = label.path
        if test is None:
            test = l
        if not test.startswith(label_type):
            continue
        m = all_labels[l]
        ret.append(m)
    return ret

@awaitable
def promise_all(*proms):
    """Wait for all promises to resolve.

    Args:
        *proms (Promise): Promises to combine.

    Returns:
        PromiseAllAny: A promise that resolves when every input promise is done.

    Example:
        await promise_all(delay_sim(seconds=5), my_task)
    """
    if len(proms)==1:
        return PromiseAllAny(*proms, True)
    return PromiseAllAny(proms, True)

@awaitable
def promise_any(*proms):
    """Wait for any one promise to resolve.

    Args:
        *proms (Promise): Promises to combine.

    Returns:
        PromiseAllAny: A promise that resolves when the first input promise is
            done.

    Example:
        await promise_any(delay_sim(seconds=5), abort_signal)
    """
    if len(proms)==1:
        return PromiseAllAny(*proms, False)
    return PromiseAllAny(proms, False)


def gui_task_jump(label):
    """Redirect the active GUI task to a new label.

    Args:
        label (str | Label): The label to jump to.
    """
    page = FrameContext.page
    if page is None:
        return PollResults.OK_ADVANCE_TRUE
    task = FrameContext.page.gui_task
    if task is not None:
        with FrameContextOverride(task, page):
            task.jump(label)
    return PollResults.OK_ADVANCE_TRUE
