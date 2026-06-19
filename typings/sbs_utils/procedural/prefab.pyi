from sbs_utils.helpers import FrameContext
from sbs_utils.futures import PromiseAllAny
def awaitable (func):
    ...
def prefab_autoname (name):
    """Return ``name`` with the ``#`` placeholder replaced by an auto-incrementing number.
    
    If ``name`` contains ``#``, the prefix before ``#`` is used as a counter
    key and the ``#`` (plus any trailing characters) is replaced with a
    zero-padded incrementing integer. Names without ``#`` are returned
    unchanged.
    
    Args:
        name (str): Name template, optionally containing ``#``.
    
    Returns:
        str: The name with ``#`` replaced by a unique number, or the original
            name if no ``#`` was found."""
def prefab_extends (label, data=None):
    """Run a prefab label as a sub-task of the current task.
    
    Unlike ``prefab_spawn``, which creates an independent task, this attaches
    the prefab as a child of the calling task and sets ``self``/``prefab``
    variables so the sub-task can refer back to its parent.
    
    Args:
        label (str | Label): The label to run as a sub-task.
        data (dict, optional): Variables passed into the sub-task. Defaults to
            None.
    
    Returns:
        MastAsyncTask: The running sub-task."""
def prefab_spawn (label, data=None, OFFSET_X=None, OFFSET_Y=None, OFFSET_Z=None):
    """Spawn a prefab label as an independent task and return it.
    
    Positional keys ``START_X``, ``START_Y``, ``START_Z`` inside ``data``
    set the spawn origin (default 0). The ``OFFSET_*`` params shift that
    origin without modifying the original ``data`` dict. If ``data`` contains
    a ``NAME`` key with a ``#`` placeholder, ``prefab_autoname`` is applied
    to generate a unique name.
    
    Args:
        label (str | Label): The label to spawn.
        data (dict, optional): Variables passed into the prefab task. May
            include ``START_X``, ``START_Y``, ``START_Z``, and ``NAME``.
            Defaults to None.
        OFFSET_X (float, optional): X offset added to ``START_X``. Defaults
            to None (no offset).
        OFFSET_Y (float, optional): Y offset added to ``START_Y``. Defaults
            to None (no offset).
        OFFSET_Z (float, optional): Z offset added to ``START_Z``. Defaults
            to None (no offset).
    
    Returns:
        MastAsyncTask: The running prefab task, or ``None`` if the label is
            invalid."""
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
class PrefabAll(PromiseAllAny):
    """class PrefabAll"""
    def __init__ (self, proms) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def result (self):
        """Get a set of the results of all of the promises.
        Returns:
            set[Promise]: The set of promise results"""
