from .. import faces, scatter
import math
import itertools
import logging
import random
from .. import fs
import sys
from inspect import getmembers, isfunction

import builtins as __builtin__
from ..helpers import FrameContext
def mast_print(*args, **kwargs):
    task = FrameContext.task 
    if len(args)==1 and task is not None:
        return __builtin__.print(task.compile_and_format_string(args[0]))
    #    args[0] = ">>>"+args[0]
    return __builtin__.print(*args, **kwargs)


class MastGlobals:
    globals = {
        "math": math, 
        "faces": faces,
        "scatter": scatter,
        "random": random,
        "print": mast_print, 
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
        "iter": iter,
        "sorted": sorted,
        "mission_dir": fs.get_mission_dir(),
        "data_dir": fs.get_artemis_data_dir(),
        #"MastDataObject": MastDataObject,
        "range": range,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "__build_class__":__build_class__, # ability to define classes
        "__name__":__name__ # needed to define classes?
    }

    def import_python_function(func, name=None):
        if name:
            MastGlobals.globals[name] = func
        else:
            MastGlobals.globals[func.__name__] = func
        

    def import_python_module(mod_name, prepend=None):
        #print(f"{mod_name}")
        sca = sys.modules.get(mod_name)
        if sca:
            for (name, func) in getmembers(sca,isfunction):
                #print(f"IMPORT {name}")
                if prepend == None:
                    MastGlobals.globals[name] = func
                elif prepend == True:
                    MastGlobals.globals[f"{mod_name}_{name}"] = func
                elif isinstance(prepend, str):
                    MastGlobals.globals[f"{prepend}_{name}"] = func


