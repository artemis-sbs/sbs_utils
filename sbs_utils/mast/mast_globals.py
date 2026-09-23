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
        # bool and float were the two numeric builtins missing from this table, so a
        # mission writing `bool(x)` or `float(x)` got NameError - and only in the engine,
        # because MAST replaces __builtins__ with this dict.
        "bool": bool,
        "float": float,
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
                # A leading underscore means "private to this module" - do NOT publish it
                # as a MAST global.
                #
                # This is a BULK, implicit export: every function in the module, whether
                # its author meant it to be part of the MAST surface or not. Publishing
                # the helpers too is actively harmful, because MAST globals and MAST
                # variables share one flat namespace - so a mission script assigning to a
                # variable that happens to match a library helper gets
                # "Variable assignment to a keyword <name>", which fails the COMPILE, and
                # a story that does not compile runs ZERO labels. That is exactly how a
                # helper named `_dist` in procedural/volume.py silently killed every
                # mission loading LegendaryMissions' ai addon (2026-08-12).
                #
                # Measured before adding this: 266 underscore functions across 82 modules
                # were reaching the globals - 261 distinct names, 31 of them short generic
                # words like _log, _now, _val, _vec - and four were already colliding with
                # EACH OTHER (_num from three modules, _lerp/_truthy/_sbs from two), where
                # the loop below merely prints a warning and lets the last one win.
                # A scan of all 611 .mast files on the dev machine found ZERO calls to any
                # of them, so nothing depended on them being published.
                #
                # Deliberately NOT applied to import_python_function: that is an explicit,
                # one-at-a-time export where the caller names the function on purpose, and
                # the base globals legitimately carry dunders like __build_class__.
                if name.startswith("_"):
                    continue
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

    class PrivateFileNamespace(dict):
        """Globals for ONE .py file, falling back to its mission's shared namespace.

        A leading underscore now really is private. Every .py of a mission used to be
        exec'd straight into one shared dict, so a top-level `_helper` in one addon
        silently replaced another addon's `_helper` - and because a function's
        `__globals__` IS that dict, the call resolved to whichever file loaded LAST.
        No error, no warning, wrong function, load-order dependent.

        It shipped: Engineering's View tab called its own `_label`, got
        `director/director_overlays.py`'s `_label` (a string sanitizer, loaded later),
        and drew no labels at all. Four rounds to find, because a unit test imports the
        file as an ordinary Python module where the name is that file's own.

        So each file gets its own globals; only PUBLIC names are published upward. A
        name this file does not define falls through to the shared namespace AT CALL
        TIME, which is what keeps cross-file bare calls working in both directions
        regardless of load order - the behavior this namespace exists for.

        `__missing__` must also answer BUILTINS: a dict SUBCLASS as globals takes
        CPython off its fast builtins path, so `range`, `len` and friends arrive here.
        Measured on the engine's own 3.11 - 3.14 resolved them without help, so this
        is exactly the kind of difference that only shows on the shipped interpreter.
        """

        def __init__(self, shared):
            super().__init__()
            self.shared = shared

        def __missing__(self, key):
            try:
                return self.shared[key]
            except KeyError:
                pass
            try:
                return getattr(__builtin__, key)
            except AttributeError:
                raise NameError(f"name '{key}' is not defined")

        # `name in globals()` and `globals().get(name)` must see the shared namespace
        # too - a bare lookup does (through __missing__), and a file that asks the other
        # way is asking the same question. dict's own `in`/`get` never call __missing__,
        # so they only saw this file's names: OpenUniverse's `admiral_present()` is
        # `"admiralty_configure" in globals()`, answered False, and the whole Admiral
        # economy - console included - silently never switched on (engine-seen
        # 2026-09-23). Builtins stay out: `in globals()` never meant builtins.
        def __contains__(self, key):
            return dict.__contains__(self, key) or key in self.shared

        def get(self, key, default=None):
            if dict.__contains__(self, key):
                return dict.__getitem__(self, key)
            return self.shared.get(key, default)

    class FileModule:
        """What `import sibling` binds for one of a mission's .py files.

        `sys.modules[<bare name>]` used to be the SHARED module, which was fine while
        every file exec'd into it. Now a file keeps its privates, so an explicit
        `import casino_amd` followed by `casino_amd._declare_casino_vocabulary()` -
        a real pattern, and one that worked before - could no longer find them.
        Caught by the ENGINE, not by the unit tests, which never wrote that form.

        So the imported name resolves attributes against the FILE first and the
        shared namespace second. That makes `sibling._private` work again, keeps
        `sibling.public` working, and needs no copying, so module-level state stays
        the one object everybody mutates.
        """

        def __init__(self, name, ns, shared):
            self.__name__ = name
            self._ns = ns
            self._shared = shared

        def __getattr__(self, key):
            # Only called when normal lookup fails, so __name__/_ns/_shared never
            # reach here.
            ns = self.__dict__.get("_ns") or {}
            if key in ns:
                return ns[key]
            shared = self.__dict__.get("_shared") or {}
            if key in shared:
                return shared[key]
            raise AttributeError(
                f"module '{self.__dict__.get('__name__')}' has no attribute '{key}'")

        def __setattr__(self, key, value):
            if key in ("__name__", "_ns", "_shared"):
                object.__setattr__(self, key, value)
            else:
                self._ns[key] = value

        def __dir__(self):
            return sorted(set(self._ns) | set(self._shared))

    def make_py_file_namespace(scope_key):
        """Per-file globals for a .py being exec'd into `scope_key`'s namespace."""
        mod = MastGlobals.get_mission_py_module(scope_key)
        ns = MastGlobals.PrivateFileNamespace(mod.__dict__)
        ns["__builtins__"] = __builtin__
        # The SHARED module's name, not the file's. A def takes its `__module__` from
        # whatever `__name__` its globals carry, and `register_mission_functions` only
        # registers functions whose `__module__` matches the shared module - that is
        # how it tells a mission's own defs from re-exported library ones. Leave this
        # out and every addon function silently stops being a MAST global: the story
        # compiles, then dies at runtime on `name 'lm_eng_crew_items' is not defined`.
        ns["__name__"] = mod.__name__
        return ns

    def publish_py_file_namespace(scope_key, ns):
        """Move a file's PUBLIC names into the shared namespace; keep its privates.

        The publics are MOVED, not copied: once published they are deleted from the
        file's own globals, so a later lookup falls through to the shared namespace.
        That keeps PUBLIC resolution exactly as it was - shared, call-time,
        last-definition-wins - and confines this change to underscored names, which is
        the whole of the fix. (`sbs lint`'s `ns-duplicate-function` is what a
        duplicated PUBLIC name is for; nothing here should quietly change which one a
        mission gets.)

        Privates stay in the file. So do dunders and the fallback's bookkeeping.
        """
        shared = MastGlobals.get_mission_py_module(scope_key).__dict__
        for key in [k for k in ns if not k.startswith("_")]:
            shared[key] = ns.pop(key)
        return MastGlobals.get_mission_py_module(scope_key)

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
        published, and the filter only removes loaded guns.
        """
        for fname, func in getmembers(mod, isfunction):
            if fname.startswith("_"):
                continue
            if getattr(func, "__module__", None) == mod.__name__:
                MastGlobals.globals[fname] = func


MastGlobals.globals["import_python_module"] = MastGlobals.import_python_module
