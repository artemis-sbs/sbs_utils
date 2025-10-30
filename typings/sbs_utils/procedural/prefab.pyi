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
def prefab_extends (*args, **kwargs):
    ...
def prefab_spawn (*args, **kwargs):
    ...
def sub_task_schedule (*args, **kwargs):
    ...
def task_schedule (*args, **kwargs):
    ...
class PrefabAll(PromiseAllAny):
    """class PrefabAll"""
    def __init__ (self, proms) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def result (self):
        """Get a set of the results of all of the promises.
        Returns:
            set[Promise]: The set of promise results"""
