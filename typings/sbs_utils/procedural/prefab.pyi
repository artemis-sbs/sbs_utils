from sbs_utils.helpers import FrameContext
from sbs_utils.futures import PromiseAllAny
def awaitable (func):
    ...
def prefab_autoname (name):
    """Apply a number to the given name if a `#` is included. Numbers are unique.
    Args:
        name (str): The name.
    Returns:
        str: The name with the number applied."""
def prefab_extends (label, data=None):
    """Add the label as a subtask of the current task.
    Args:
        label (str | Label): The label to run
        data (dict): The data associated with the prefab.
    Returns:
        MastAsyncTask: The prefab"""
def prefab_spawn (label, data=None, OFFSET_X=None, OFFSET_Y=None, OFFSET_Z=None):
    """Spawn a prefab and return its task.
    Args:
        label (str | Label): The label to run to spawn the prefab.
        data (dict, optional): Data associated with the prefab.
        * Positional data may be optionally included in `data`: `START_X`, `START_Y`, and `START_Z`. The default for these all is 0.
        OFFSET_X (int, optional): The X offset relative to the positional data. Default is None.
        OFFSET_Y (int, optional): The Y offset relative to the positional data. Default is None.
        OFFSET_Z (int, optional): The Z offset relative to the positional data. Default is None.
    Returns:
        MastAsyncTask: The task of the prefab."""
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
class PrefabAll(PromiseAllAny):
    """class PrefabAll"""
    def __init__ (self, proms) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def result (self):
        """Get a set of the results of all of the promises.
        Returns:
            set[Promise]: The set of promise results"""
