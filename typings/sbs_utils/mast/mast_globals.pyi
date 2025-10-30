from sbs_utils.helpers import FrameContext
def getmembers (object, predicate=None):
    ...
def isfunction (object):
    ...
def mast_print (*args, use_mast_scope=True, **kwargs):
    ...
class MastGlobals(object):
    """class MastGlobals"""
    def import_python_function (func, name=None):
        """Import a python function as a global and optionally specify a name for it.
        Args:
            func (Callable): The python function
            name (str|None): The name assinged to the function (optional, default is None)."""
    def import_python_module (mod_name, prepend=None):
        """Import all functions within a python module as globals and optionally add a prepend to the function names.
        For example, the functions in the `scatter` module are added as global functions with 'scatter' prepended to the name like so:
        ```python
        MastGlobals.import_python_module('sbs_utils.scatter', 'scatter')
        ```
        This allows the functions in the scatter module to be called, e.g. `scatter_arc(...args)`
        Args:
            mod_name (str): The name of the module
            prepend (str): The string to prepend to the function names"""
