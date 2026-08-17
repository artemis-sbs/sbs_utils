from sbs_utils.helpers import FrameContext
def debug_print (*args, **kwargs):
    ...
def getmembers (object, predicate=None):
    """Return all members of an object as (name, value) pairs sorted by name.
    Optionally, only return members that satisfy a given predicate."""
def getmodule (object, _filename=None):
    """Return the module an object was defined in, or None if not found."""
def isfunction (object):
    """Return true if the object is a user-defined function.
    
    Function objects provide these attributes:
        __doc__         documentation string
        __name__        name with which this function was defined
        __qualname__    qualified name of this function
        __module__      name of the module the function was defined in or None
        __code__        code object containing compiled function bytecode
        __defaults__    tuple of any default values for arguments
        __globals__     global namespace in which this function was defined
        __annotations__ dict of parameter annotations
        __kwdefaults__  dict of keyword only parameters with defaults
        __dict__        namespace which is supporting arbitrary function attributes
        __closure__     a tuple of cells or None
        __type_params__ tuple of type parameters"""
def mast_print (*args, use_mast_scope=True, **kwargs):
    ...
def version_get ():
    ...
def version_get_build ():
    ...
def version_get_major ():
    ...
def version_get_minor ():
    ...
class MastGlobals(object):
    """class MastGlobals"""
    def get_mission_py_module (scope_key):
        """Get-or-create the shared namespace module for a mission (by basedir).
        
        Real builtins are present (so float/Exception/getattr/etc. keep working),
        unlike MastGlobals.globals which is a curated MAST-eval whitelist."""
    def import_python_function (func, name=None):
        """Import a python function as a global and optionally specify a name for it.
        Args:
            func (Callable): The python function
            name (str|None): The name assinged to the function (optional, default is None)."""
    def import_python_module (mod_name, prepend=None, allow_mismatch=False, use_decorator=False):
        """Import all functions within a python module as globals and optionally add a prepend to the function names.
        For example, the functions in the `scatter` module are added as global functions with 'scatter' prepended to the name like so:
        ```python
        MastGlobals.import_python_module('sbs_utils.scatter', 'scatter')
        ```
        This allows the functions in the scatter module to be called, e.g. `scatter_arc(...args)`
        Args:
            mod_name (str): The name of the module
            prepend (str): The string to prepend to the function names"""
    def register_mission_functions (mod):
        """Register the functions DEFINED in a mission's or addon's shared namespace as
        MAST globals so .mast can call them. Functions imported from libraries keep their
        own __module__, so only this namespace's own defs are added (not re-exports).
        
        UNDERSCORE NAMES ARE SKIPPED, for the same reason and with the same evidence as
        `import_python_module` above - which is where that filter was added in 2026-08-12,
        and only there. This is the OTHER path into the one flat, mission-wide namespace:
        the library goes through that one, every addon's .py comes through here. So a
        leading underscore stopped being published by the library and went on being
        published by every mod, which is not a rule anyone could hold in their head.
        
        It is not just a tidiness argument. The collision that matters is not
        function-vs-function (the loop below merely lets the last one win, with a warning)
        but function-vs-MAST-VARIABLE: an addon exporting `_mine` turns
        `_mine = to_object(closest(...))` in ANOTHER addon's .mast into the compile error
        "Variable assignment to a keyword", and a story that does not compile runs ZERO
        labels. A28-Skybox-Mod's `_mine` did exactly that to LegendaryMissions' autoplay -
        every mission loading both was dead, in silence, with the error pointing at
        autoplay rather than at the pack that caused it.
        
        Measured before adding this, the same way: 104 underscore-prefixed defs across the
        addon .py files on this machine were reaching the globals, ZERO .mast files called
        any of them, and none collided with each other - so nothing depends on them being
        published, and the filter only removes loaded guns."""
