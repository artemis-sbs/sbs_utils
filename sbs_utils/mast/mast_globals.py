from .. import faces, scatter
import math
import itertools
import logging
import random
from .. import fs
import sys
import types
from inspect import getmembers, isfunction, getmodule
from ..version__ import version_get, version_get_major, version_get_build, version_get_minor
import json

import builtins as __builtin__
from ..helpers import FrameContext
def mast_print(*args, use_mast_scope=True, **kwargs):
    task = FrameContext.task 
    if use_mast_scope and len(args)==1 and task is not None:
        return __builtin__.print(task.compile_and_format_string(args[0]))
    #    args[0] = ">>>"+args[0]
    return __builtin__.print(*args, **kwargs)

def debug_print(*args, **kwargs):
    if fs.is_dev_build():
        mast_print(*args, **kwargs)

class MastGlobals:
    _imported_mods = set()
    globals = {
        "math": math,
        "json" : json,
        "faces": faces,
        "scatter": scatter,
        "random": random,
        "print": mast_print,
        "debug_print":debug_print,
        "dir":dir, 
        "itertools": itertools,
        "next": next,
        "len": len,
        "reversed": reversed,
        "int": int,
        "str": str,
        "hex": hex,
        "min": min,
        "max": max,
        "abs": abs,
        "sim": None,
        "map": map,
        "filter": filter,
        "list": list,
        "set": set,
        "dict": dict,
        "tuple": tuple,
        "zip": zip,
        "enumerate": enumerate,
        "iter": iter,
        "sorted": sorted,
        "mission_dir": fs.get_mission_dir(),
        "data_dir": fs.get_artemis_data_dir(),
        "version_get": version_get,
        "version_get_major": version_get_major,
        "version_get_build": version_get_build,
        "version_get_minor": version_get_minor,
        #"MastDataObject": MastDataObject,
        "range": range,
        "isinstance": isinstance,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "__build_class__":__build_class__, # ability to define classes
        "__name__":__name__ # needed to define classes?
    }

    def import_python_function(func, name=None):
        """
        Import a python function as a global and optionally specify a name for it.
        Args:
            func (Callable): The python function
            name (str|None): The name assinged to the function (optional, default is None).
        """
        if name:
            MastGlobals.globals[name] = func
        else:
            MastGlobals.globals[func.__name__] = func
        

    def import_python_module(mod_name, prepend=None, allow_mismatch=False, use_decorator=False):
        """
        Import all functions within a python module as globals and optionally add a prepend to the function names.
        For example, the functions in the `scatter` module are added as global functions with 'scatter' prepended to the name like so:
        ```python
        MastGlobals.import_python_module('sbs_utils.scatter', 'scatter')
        ```
        This allows the functions in the scatter module to be called, e.g. `scatter_arc(...args)`
        Args:
            mod_name (str): The name of the module
            prepend (str): The string to prepend to the function names
        """
        
        if mod_name in MastGlobals._imported_mods:
            return
        
        from importlib import import_module
        sca = sys.modules.get(mod_name)
        if sca is None:
            sca = import_module(mod_name)
        if sca:
            for (name, func) in getmembers(sca,isfunction):
                # actual_mod = getmodule(func).__name__
                # # This is a work around where importing
                # # A python file in MAST was re adding 
                # # modules, with the wrong module names
                # if ":" in actual_mod.__name__:
                #     print(f"skipping {name} {mod_name} != {actual_mod}")
                #     continue
                if hasattr(func, "__wrapped__"):
                    func = func.__wrapped__
                actual_mod = func.__module__
                if mod_name not in actual_mod and not allow_mismatch:
                    continue

                if prepend == None:
                    key = name
                elif prepend == True:
                    
                    key = f"{mod_name}_{name}"
                elif isinstance(prepend, str):
                    key = f"{prepend}_{name}"

                if key in MastGlobals.globals:
                    if func == MastGlobals.globals[key]:
                        continue
                    print(f"Duplicate global name added {name} via import of module {mod_name}")
                MastGlobals.globals[key] = func
        MastGlobals._imported_mods.add(mod_name)

    # One shared Python namespace per mission (keyed by basedir). All of a mission's
    # addon .py files are exec'd into this single module dict so a helper in one file
    # can call a helper in a sibling file by bare name - the "one shared MAST
    # namespace" the mission docs describe. (Mastlib .py is unaffected; it still
    # loads one module per file.) MAST variables are NOT stored here - they live in
    # task scope - so this can neither shadow nor be shadowed by a MAST variable.
    mission_py_modules = {}

    def get_mission_py_module(scope_key):
        """Get-or-create the shared namespace module for a mission (by basedir).

        Real builtins are present (so float/Exception/getattr/etc. keep working),
        unlike MastGlobals.globals which is a curated MAST-eval whitelist.
        """
        key = scope_key or "<mission>"
        mod = MastGlobals.mission_py_modules.get(key)
        if mod is None:
            mod = types.ModuleType("mast_mission_py::" + str(key))
            mod.__dict__["__builtins__"] = __builtin__
            MastGlobals.mission_py_modules[key] = mod
            sys.modules[mod.__name__] = mod
        return mod

    def register_mission_functions(mod):
        """Register the functions DEFINED in a mission's shared namespace as MAST
        globals so .mast can call them. Functions imported from libraries keep their
        own __module__, so only this mission's own defs are added (not re-exports)."""
        for fname, func in getmembers(mod, isfunction):
            if getattr(func, "__module__", None) == mod.__name__:
                MastGlobals.globals[fname] = func


MastGlobals.globals["import_python_module"] = MastGlobals.import_python_module
