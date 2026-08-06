from enum import Enum
import re
import ast
import os
from pathlib import Path
from .. import fs
from zipfile import ZipFile

from ..agent import Agent
import logging
import random

import sys
from ..helpers import format_exception
import json
from .mast_globals import MastGlobals
from .mast_node import MastNode, Scope
from .first_chars import first_chars_for_pattern
from .mast_linejoin import join_bracket_continuations


# --- compiler dispatch by first character ------------------------------------
# Trying every node's regex on every line is O(nodes x lines). For each line we
# instead try only nodes whose rule can possibly match the line's first char.
# This never reorders nodes (it skips ones that provably cannot match), so the
# "first match wins" semantics are preserved. See first_chars.py for the safety
# invariant (uncertain -> matches-anything -> never skipped).
_node_first_chars_cache = {}   # node_cls -> set[str] | None  (None == any)
_candidate_cache = {}          # first_char -> tuple(node_cls, ...)
_candidate_cache_count = -1    # len(MastNode.nodes) the caches were built for


def _node_first_chars(node_cls):
    cached = _node_first_chars_cache.get(node_cls, "?")
    if cached != "?":
        return cached
    rule = getattr(node_cls, "rule", None)
    fc = None if rule is None else first_chars_for_pattern(rule.pattern)
    _node_first_chars_cache[node_cls] = fc
    return fc


def _candidates_for(nodes, ch):
    out = []
    for nc in nodes:
        fc = _node_first_chars(nc)
        if fc is None or ch in fc:
            out.append(nc)
    return tuple(out)


class CompileContext:
    """Per-compile scratch state for block-structured nodes.

    if/match/await/on/for nodes need to track their open blocks while parsing.
    This state used to live as class attributes on the node types and was shared
    across every compile, so an aborted compile (we bail early on the first
    error) or a nested import (imports compile recursively mid-parse) could
    corrupt the next/outer compile -- e.g. `if_chains` keyed only by indent could
    alias unrelated blocks. Each `_compile` now gets its own context, reached by
    nodes through `compile_info.ctx`.
    """
    __slots__ = ("if_chains", "match_chains", "await_stack",
                 "on_change_stack", "on_signal_stack", "loop_stack")

    def __init__(self):
        self.if_chains = {}        # IfStatements: indent -> active if (or None)
        self.match_chains = []     # MatchStatements: stack of open matches
        self.await_stack = []      # Await: stack of open awaits
        self.on_change_stack = []  # OnChange: stack of open on-change blocks
        self.on_signal_stack = []  # OnSignal: stack of open on-signal blocks
        self.loop_stack = {}       # LoopStart: indent -> active loop (or None)


class SourceMapData:
    def __init__(self, file_name, basedir):
        self.file_name = file_name
        self.basedir = basedir
        self.is_lib = False

    def __str__(self):
        return f"{self.file_name} ({self.basedir})"

debug_logger = None
def DEBUG(msg):
    global debug_logger
    if debug_logger is None:
        # create logger with 'spam_application'
        debug_logger = logging.getLogger('debug')
        debug_logger.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        fh = logging.FileHandler('debug.log', mode='w')
        fh.setLevel(logging.DEBUG)
        debug_logger.addHandler(fh)
    debug_logger.debug(msg)



class Rule:
    def __init__(self, re, cls):
        self.re = re
        self.cls = cls



# Open .mastlib handles, reused for the duration of ONE compile.
#
# content_from_lib_or_file() is called once per file, and a mastlib holds many
# files, so opening the zip per read re-parsed the same central directory over and
# over (measured: OpenUniverse did 124 opens for its 21 declared libs, ~56ms of
# pure ZipFile.__init__; now 21 opens, ~9ms). _lib_zip_scope closes them when the
# outermost compile unwinds - deliberately not held longer, so nothing keeps a
# Windows file lock on a .mastlib that a rebuild wants to replace.
_lib_zip_cache = {}


def _open_lib_zip(lib_name):
    z = _lib_zip_cache.get(lib_name)
    if z is None:
        z = ZipFile(lib_name)
        _lib_zip_cache[lib_name] = z
    return z


def close_lib_zips():
    """Drop every cached .mastlib handle. Safe to call at any time; the next read
    reopens."""
    for z in _lib_zip_cache.values():
        try:
            z.close()
        except Exception:
            pass
    _lib_zip_cache.clear()


_compile_depth = 0


class _lib_zip_scope:
    """Own the .mastlib handle cache for the OUTERMOST compile, whichever public
    entry point that is. Nested calls ride the same cache; the outermost one closes
    it on the way out, including on exceptions.

    Depth-counted rather than keyed on `root is None`, because import_content() is
    a legitimate standalone entry (tooling and tests call it with a non-None root).
    Keying on root leaked a handle there and left a Windows lock on the .mastlib -
    the caller then could not delete or rebuild it.
    """
    def __enter__(self):
        global _compile_depth
        _compile_depth += 1
        return self

    def __exit__(self, *exc):
        global _compile_depth
        _compile_depth -= 1
        if _compile_depth <= 0:
            _compile_depth = 0
            close_lib_zips()
        return False


def first_non_space_index(s):
    for idx, c in enumerate(s):
        if not c.isspace():
            return idx
        if c == '\n':
            return idx
    return len(s)


def first_non_newline_index(s, start=0):
    # Returns the absolute index of the first non-newline char at/after start.
    n = len(s)
    for idx in range(start, n):
        if s[idx] != '\n':
            return idx
    return n

def first_non_whitespace_index(s, start=0):
    # Scans from start; returns absolute indices so the caller can advance a
    # cursor instead of slicing the source (which would be O(n^2)).
    nl = 0
    nl_idx = start
    n = len(s)
    for idx in range(start, n):
        c = s[idx]
        if c != '\n' and c != '\t' and c != ' ':
            return (idx, nl, nl_idx)
        if c == '\n':
            nl += 1
            nl_idx = idx
    return (n, nl, nl_idx)

def first_newline_index(s, start=0):
    n = len(s)
    for idx in range(start, n):
        if s[idx] == '\n':
            return idx
    return n


class ExpParseData:
    def __init__(self):
        self.in_string = False
        self.paren = 0
        self.bracket = 0
        self.brace = 0
        self.is_assign = False
        self.is_block = False
        self.idx = -1
        self.double_assign = False

    @property
    def in_something(self):
        return self.in_string or (self.paren>0) or (self.bracket>0) or (self.brace>0)
    @property
    def is_valid(self):
        return not (self.in_something or self.double_assign)

def find_exp_end(s, expect_block):
    data = ExpParseData()

    for idx, c in enumerate(s):
        if c == '\n' and not data.in_something:
            data.idx = idx
            return data
        if c == '=' and not data.in_something and not data.is_assign:
            data.is_assign = True
            continue
        elif c == '=' and not data.in_something and data.is_assign:
            data.double_assign = True
            return data
        
        if c == ':' and not data.in_something and expect_block:
            data.is_block = True
            data.idx = idx
            return data
        
        if c == '(' and not data.in_string:
            data.paren+=1
            continue
        if c == ')' and not data.in_string:
            data.paren-=1
            continue
        if c == '[' and not data.in_string:
            data.bracket+=1
            continue
        if c == ']' and not data.in_string:
            data.bracket-=1
            continue
        if c == '{' and not data.in_string:
            data.brace+=1
            continue
        if c == '}' and not data.in_string:
            data.brace-=1
            continue
        if c == '"' and not data.in_string:
            data.in_string = True
            continue
        if c == '"' and data.in_string:
            data.in_string = False
            continue

    data.idx = len(s)
    return data

class InlineData:
    def __init__(self, start, end):
        self.start = start
        self.end = end


# IMPORTING other nodes should not happen here
# It can screw up the order
from .core_nodes.comment import Comment
#### This one really break stuff
#### from .core_nodes import Assign



class Mast():
    include_code = False

    # Optional verdict/trace seam. When set to a callable, a compile that produces
    # errors invokes ``on_compile_error(errors, file_name)``. Default ``None`` → a
    # single ``is not None`` check, no overhead; never set in the shipped library.
    # Used by dev tooling (cosmos_dev MastVerdict) to turn a headless --test into a
    # pass/fail on COMPILE errors too, not just runtime errors (the engine surfaces
    # compile errors; the mock previously ran on with the bad file silently empty).
    on_compile_error = None

    inline_count = 0
    source_map_files = []

    def __init__(self, cmds=None, is_import=False):
        super().__init__()

        self.lib_name = None
        self.is_import = is_import
        self.basedir = None
        self.parent_basedir = None
        self.compiler_errors = []
        # Per-story import dedup. from_file tracks already-imported files in
        # root.imported (the top story's dict); nested imports thread `root`
        # through, so they share it within one compile. This MUST be per-instance:
        # as a class attribute it was shared across every Mast/MastStory ever
        # created, so a second story loading a file a previous story already
        # imported would short-circuit and skip compiling it entirely.
        self.imported = {}
        # Addon dependency manifest (accumulated on the ROOT story as each file
        # compiles - see the Provides/Requires/Suggests handling in compile()).
        # provides: set of capability tokens; requires: list of
        # (token, kind, file_name, line_no, line) where kind is "requires"|"suggests".
        self.provides = set()
        self.requires = []


        if cmds is None:
            self.clear("no_mast_file", self)
        elif isinstance(cmds, str):
            cmds = self.compile(cmds, "<string>")
        # else:
        #     self.build(cmds)
        if not is_import:
            for logger_name, log_file in (("mast.compile", 'mast.compile.log'),
                                          ("mast.runtime", 'mast.runtime.log')):
                mc = logging.getLogger(logger_name)
                # Drop FileHandlers from a previous Mast() so they don't pile up
                # (each compile re-opens the log fresh; "w" truncates it).
                for h in list(mc.handlers):
                    if isinstance(h, logging.FileHandler):
                        mc.removeHandler(h)
                        h.close()
                fn = fs.get_mission_dir_filename(log_file)
                mc.addHandler(logging.FileHandler(fn, "w"))


    def make_global(func):
        add_to = MastGlobals.globals
        add_to[func.__name__] = func


    def make_global_var(name, value):
        MastGlobals.globals[name] = value
        
    

    def import_python_module_for_source(self, name, lib_name):
        import importlib, importlib.abc

        class StringLoader(importlib.abc.SourceLoader):
            def __init__(self, data):
                self.data = data

            def get_source(self, fullname):
                return self.data
            
            def get_data(self, path):
                return self.data.encode("utf-8")
            
            def get_filename(self, fullname):
                return "<not a real path>/" + fullname + ".py"

        module_name = name[:-3]

        # Library (.mastlib) python: exec every .py of one mastlib into a SINGLE shared
        # namespace (keyed by lib_name), so a helper in one file can call a sibling
        # file's helper by bare name - the same "one shared MAST namespace" a local
        # mission addon gets (get_mission_py_module). Previously each mastlib .py loaded
        # as an ISOLATED module, so a bare-name cross-file call NameErrored once the addon
        # was packaged (e.g. an OpenUniverse .py calling a sibling's helper) - fine as a
        # local folder, broken as a mastlib. Sharing is a superset of isolation (explicit
        # `import sibling` still resolves via sys.modules below); functions are still
        # registered into MastGlobals.globals for MAST-level calls.
        if self.lib_name is not None:
            # content_from_lib_or_file mutates self.basedir to the loaded file's
            # directory (that cursor is how nested .mast imports resolve). A .py import
            # reuses `self`, so save/restore the base or the mutation leaks into the
            # NEXT sibling import.
            saved_basedir = self.basedir
            content, errors = self.content_from_lib_or_file(name)
            self.basedir = saved_basedir
            if content is None:
                raise Exception(f"Failed to import python in mast library {name} {self.lib_name}")
            ns_mod = MastGlobals.get_mission_py_module(self.lib_name)
            # Expose the shared namespace under this file's bare module name so a
            # `from sibling import x` / `import sibling` between the mastlib's .py files
            # resolves to the shared dict. Idempotent; set before exec.
            sys.modules[module_name] = ns_mod
            exec_files = ns_mod.__dict__.setdefault("__mast_files__", set())
            if name in exec_files:
                return
            exec(compile(content, "<not a real path>/" + module_name + ".py", "exec"), ns_mod.__dict__)
            exec_files.add(name)
            MastGlobals.register_mission_functions(ns_mod)
            return

        # Mission addon python: exec every .py of one mission into a single shared
        # namespace so a helper in one file can call a sibling file's helper by bare
        # name. Keyed by the MISSION DIR, not self.basedir - so a mission's LOCAL SIBLING
        # addon folders (e.g. OpenUniverse's universe_core/ + admiral/ + fabrication/)
        # all share ONE namespace and cross-call both directions, the way they did when
        # they were a single folder before the Phase 2b split. (Keying by the per-addon
        # basedir put each folder in its own namespace, so admiral's universe_worldlets.py
        # couldn't see universe_core's universe_section, and universe_core's admiral_present
        # couldn't see admiral's admiralty_configure -> the Admiral console silently
        # vanished.) Functions are still registered into MastGlobals.globals for MAST-level
        # calls. (See MastGlobals.get_mission_py_module.) self.basedir still locates the file.
        if os.path.isfile(os.path.join(self.basedir, name)):
            import_file_name = os.path.join(self.basedir, name)
        else:
            import_file_name = os.path.join(fs.get_mission_dir(), name)
        ns_mod = MastGlobals.get_mission_py_module(fs.get_mission_dir())
        # Expose the shared namespace under this file's bare module name so existing
        # `from sibling import x` / `import sibling` Python imports between a mission's
        # .py files keep working - the symbols live in the shared dict. Idempotent;
        # set before exec so a file importing a sibling already loaded resolves it.
        sys.modules[module_name] = ns_mod
        # Per-mission dedup: don't re-exec a file already loaded into this namespace.
        exec_files = ns_mod.__dict__.setdefault("__mast_files__", set())
        if import_file_name in exec_files:
            return
        with open(import_file_name, "r") as pyfile:
            content = pyfile.read()
        exec(compile(content, import_file_name, "exec"), ns_mod.__dict__)
        exec_files.add(import_file_name)
        MastGlobals.register_mission_functions(ns_mod)



    nodes = MastNode.nodes

    def get_source_file_name(file_num):
        if file_num is None:
            return "<string>"
        if file_num >= len(Mast.source_map_files):
            return "<unknown>"
        return str(Mast.source_map_files[file_num])

    def clear(self, file_name, root):
        from .core_nodes import Label

        self.inputs = {}
        if not self.is_import:
            #self.set_inventory_value("mast", self)
            Agent.SHARED.set_inventory_value("SHARED", Agent.SHARED.get_id())
            Mast.source_map_files = []
            

        # self.vars = {"mast": self}
        self.labels = {}
        self.inline_labels = {}
        main = Label("main")
        if root is not None:
            main = root.labels.get("main", main)
        self.labels["main"] = main
        self.labels["$NOOP$"] = Label("$NOOP$")
        self.cmd_stack = [main]
        self.indent_stack = [0]
        self.main_pruned = False
        #self.lib_name = None
        #### runtime
        self.schedulers = set()
        self.signal_observers = {}

        map_data = SourceMapData(file_name, self.basedir)
        if self.lib_name is not None:
            map_data.basedir = self.lib_name
            map_data.is_lib = True


        Mast.source_map_files.append(map_data)
        return len(Mast.source_map_files)-1
                
    
    def prune_main(self):
        from .core_nodes.assign import Assign

        if self.main_pruned:
            return
        main = self.labels.get("main")
        # Convert all the assigned from the main into comments
        # removing is bad it will affect if statements
        # If statements may run twice?
        #
        if main is not None:
            for i in range(len(main.cmds)):
                cmd = main.cmds[i]
                if cmd.__class__ == Assign and cmd.scope == Scope.SHARED:
                    main.cmds[i] = Comment()
            self.main_pruned = True

    def add_scheduler(self, scheduler):
        self.schedulers.add(scheduler)

    def refresh_schedulers(self, source, label):
        """TODO: Deprecate for signals?

        Args:
            source (_type_): _description_
            label (_type_): _description_
        """
        for scheduler in self.schedulers:
            if scheduler == source:
                continue
            scheduler.refresh(label)


    def signal_register(self, name, task, label_info):
        if label_info.server and not task.main.is_server():
            return

        task_map = self.signal_observers.get(name, {})
        info_list = task_map.get(task, [])
        info_list.append(label_info)
        task_map[task] = info_list
        self.signal_observers[name] = task_map

    def signal_unregister(self, name, task):
        #
        # note:
        #    Not sure this is written logically correct
        #
        info = self.signal_observers.get(name,None)
        if info is None:
            return
        if task in info:
            del info[task]
            self.signal_observers[name] = info

    def signal_unregister_all(self, task):
        #
        # note:
        #    Not sure this is written logically correct
        #
        for name in self.signal_observers:
            info = self.signal_observers[name]
            if info is None:
                return
            if task in info:
                del info[task]
                self.signal_observers[name] = info

    def signal_unregister_all_inline(self, task):
        # Look for any signal using the task
        for name in self.signal_observers:
            info = self.signal_observers[name]
            if info is None:
                return
            # If the loc is not 0 its inline and not jump
            if task in info:
                info_list = [i for i in info[task] if i.is_jump]
                if len(info_list)==0:
                    del info[task]
                elif len(info_list) != len(info[task]):
                    # print(f"Purged {name}")
                    info[task] = info_list
            self.signal_observers[name] = info

    def signal_emit(self, name, sender_task, data):
        # Copy so we can remove if needed
        tasks = self.signal_observers.get(name, {}).copy()
        #
        #TODO: This should remove finished tasks
        #
        for task in tasks:
            if task.done():
                self.signal_unregister(name, task)
                continue
            label_info_list = tasks[task]
            for label_info in label_info_list:
                if label_info.server and not task.main.is_server():
                    continue
                task.emit_signal(name, sender_task, label_info, data)

    def update_shared_props_by_tag(self, tag, props, test):
        for scheduler in self.schedulers:
            if scheduler.page is not None:
                scheduler.page.update_props_by_tag(tag, props, test)


    def remove_scheduler(self, scheduler):
        # End and remove all tasks
        for task in scheduler.tasks:
            task.end()
            scheduler.tasks.remove(task)
        self.schedulers.remove(scheduler)

    def find_imports(self, folder):
        import os
        imports = []
        for root, dirs, files in os.walk(os.path.join(self.basedir, folder)):
            # Avoids dev .git or .build, .add_ons etc.
            if os.path.basename(root).startswith("."):
                continue
            for name in files:
                if name.endswith("__init__.mast"):
                    p = os.path.join(root, name)
                    #DEBUG(p)
                    imports.append(p)
        return imports
    
    def find_add_ons(self):
        """The addons to compile into this story: the mastlibs its story.json declares.

        Dependencies are DECLARED, never discovered. This used to also walk the mission
        tree adopting any `.mastlib`/`.zip` it found, from before story.json + __lib__
        managed dependencies; that walk is obsolete and was actively harmful:

          * A stray archive in a mission SUBFOLDER (an art pack, a backup, an old build)
            was treated as an addon. A `.zip` has no `__init__.mast`, so the read failed
            and the story compiled to ZERO labels - and reported PASS, because the error
            only ever surfaced on the engine's on-screen error page.
          * A stale `.mastlib` was worse: it loaded fine and merged its labels in, so a
            mission silently ran content its story.json never declared.

        It could not even see the mission ROOT (the walk root was `<mission>/.`, whose
        basename tripped its own skip-hidden-directories rule), so only SUBfolders were
        ever adopted - and it walked the whole tree on every compile to produce a list
        that __lib__ had already made unnecessary.
        """
        import os
        addons = []
        is_test = sys.modules.get('script')
        if is_test is None or isinstance(is_test, str):
            return []

        script_dir = fs.get_script_dir()
        missions_dir = fs.get_missions_dir()
        story_settings = os.path.join(script_dir,"story.json")
        lib_dir = os.path.join(missions_dir,"__lib__")
        if not os.path.exists(story_settings):
            return []
        with open(story_settings, 'r') as file:
            data = json.load(file)
            # No file that's OK
            if data is None:
                return addons
            mastlibs = data.get("mastlib", [])
            skipped = []
            for file in mastlibs:
                # SOURCE WINS. A repo that packages its own addons declares them like any
                # consumer, but a CLONE still has the folders - and the two loaders are
                # additive, so loading both compiles every label twice and dies on the
                # process-global name registry with "Label conflicts with shared name",
                # which says nothing about the real cause. Preferring the source lets one
                # story.json serve both: a clone edits its addons in place, a fetched copy
                # (folders stripped by export-ignore) uses __lib__.
                src = self.addon_source_folder(script_dir, file)
                if src is not None:
                    skipped.append(os.path.basename(src))
                    continue
                f = os.path.join(lib_dir, file)
                addons.append(f)
            if skipped:
                # Announced, not silent: normal for a repo running from its own clone, but
                # for a CONSUMER it means an addon folder it probably did not mean to ship
                # is overriding the declared lib - and that used to be a hard error. One
                # summary line rather than one per addon, so a 34-addon clone is not noise.
                shown = ", ".join(skipped[:6])
                if len(skipped) > 6:
                    shown += f", +{len(skipped) - 6} more"
                print(f"Using mission SOURCE for {len(skipped)} declared addon(s) "
                      f"instead of __lib__: {shown}")

        return addons

    @staticmethod
    def addon_source_folder(mission_dir, lib_name):
        """The mission-local source folder for a declared mastlib, or None.

        A lib is named ``{user}.{repo}.{folder}.{version}.{ext}``, so the addon folder is
        the third dot-segment. Answers None unless that folder holds an ``__init__.mast`` -
        the same test find_imports uses to call something an addon, so a mission that
        merely happens to have a same-named folder cannot suppress a lib it needs.
        """
        import os
        parts = str(lib_name).split(".", 3)
        if len(parts) < 4:
            return None
        folder = os.path.join(mission_dir, parts[2])
        if os.path.isfile(os.path.join(folder, "__init__.mast")):
            return folder
        return None
    

    def expand_resources(self):
        script_dir = fs.get_script_dir()
        missions_dir = fs.get_missions_dir()
        story_settings = os.path.join(script_dir,"story.json")
        lib_dir = os.path.join(missions_dir,"__lib__")
        if not os.path.exists(story_settings):
            return
        with open(story_settings, 'r') as file:
            data = json.load(file)
            res_zips = data.get("resources", {})
            for folder, zip_name in res_zips.items():
                z = os.path.join(lib_dir, zip_name)
                f = os.path.join(script_dir, folder)
                fs.expand_zip(z, f)
                
        

            
    def from_file(self, file_name, root):
        """Compile `file_name` and everything it pulls in.

        `root is None` means this is the ROOT compile of a story; nested imports
        pass the root through. The scope guard owns the .mastlib handle cache for
        the outermost compile only.
        """
        with _lib_zip_scope():
            return self._from_file(file_name, root)

    def _from_file(self, file_name, root):
        """ Docstring"""
        if root is None:
            root = self # I am root
            #
            # Expand any dependant resources
            #
            self.expand_resources()

        # Already imported: return an empty error list, not None. Every other path
        # returns a list, and callers do len() on the result (e.g. MastStoryPage
        # stores it as self.compiler_errors, then present() does len(...)). A bare
        # return here left compiler_errors None -> "len(None)" crash on present.
        if self.lib_name is None and root.imported.get(file_name):
            return []
        elif self.lib_name is not None and root.imported.get(f"{self.lib_name}::{file_name}"):
            return []

        if self.lib_name is None:
            root.imported[file_name] = True
        else: 
            root.imported[f"{self.lib_name}::{file_name}"] = True

        content = None
        errors= None


        content, errors = self.content_from_lib_or_file(file_name)

        if errors is not None:
            # Same dev seam compile() uses, one stage earlier. A file that cannot be READ
            # returns here and never reaches compile(), so the harness never saw it: a
            # mastlib whose __init__.mast is missing (e.g. an archive that nests the addon
            # folder) loaded nothing, and a headless --test still reported PASS because the
            # only visible surface was the on-screen error page. Hook defaults to None, so
            # this is a no-op in the shipped engine.
            if Mast.on_compile_error is not None:
                try:
                    Mast.on_compile_error(errors, file_name)
                except Exception:
                    pass
            return errors
        if content is not None:
            content = content.replace("\r","")
            errors = self.compile(content, file_name, root)

                
            if len(errors) == 0 and not self.is_import:
                addons = self.find_add_ons()
                for name in addons:
                    errors = self.import_content("__init__.mast", root, name)
                    if len(errors)>0:
                        return errors

                imports = self.find_imports(".")
                for name in imports:
                    errors = self.import_content(name, root, None)
                    if len(errors)>0:
                        return errors

                # Every addon has now compiled, so the `provides` union is complete.
                # Validate declared `requires`/`suggests` (order-independent barrier).
                errors.extend(self._validate_requirements())

        return errors
            

        return []
        

    def content_from_lib_or_file(self, file_name):
        try:
            if self.lib_name is not None:
                lib_name = self.lib_name
                if ":" not in self.lib_name:
                    lib_name = os.path.join(fs.get_mission_dir(), self.lib_name)

                # Cached handle: NOT a `with`, so the zip stays open for the rest of
                # this compile (see _open_lib_zip). _lib_zip_scope closes it.
                lib_file = _open_lib_zip(lib_name)
                #
                # NOTE: Zip files must use /
                #
                if self.basedir is not  None:
                    file_name = os.path.join(self.basedir, file_name).replace("\\", '/')
                elif self.parent_basedir is not None:
                    file_name = os.path.join(self.parent_basedir, file_name).replace("\\", '/')

                with lib_file.open(file_name) as f:
                    DEBUG(f"DEBUG: {self.lib_name} {file_name}")
                    content = f.read().decode('UTF-8')
                    self.basedir = os.path.dirname(file_name)
                    return content, None

            else:
                og_file_name = file_name
                if self.basedir is not  None:
                    file_name = os.path.join(self.basedir, file_name)
                elif self.parent_basedir is not None:
                    file_name = os.path.join(self.parent_basedir, file_name)
                else:
                    file_name = os.path.join(fs.get_mission_dir(), file_name)
                # if not found in the basedir or parent basedir
                if not os.path.isfile(file_name):
                    file_name = os.path.join(fs.get_mission_dir(), og_file_name)

                self.basedir = os.path.dirname(file_name)
                    
                with open(file_name) as f:
                    content = f.read()
                return content, None
        except Exception as e:
            # Surface the underlying cause (permission, decode, missing zip
            # entry, ...) instead of a bare except that also swallowed
            # KeyboardInterrupt/SystemExit and hid the real reason.
            if self.lib_name is not None:
                message = f"File load error\nCannot load file {file_name} from library {self.lib_name}\n{e}"
            else:
                message = f"File load error\nCannot load file {file_name}\n{e}"
            return None, [message]
            
        
    

    def import_content(self, filename, root, lib_name):
        # Also a public entry point (tooling/tests call it directly), so it takes
        # the scope guard too - otherwise a .mastlib opened here is never closed.
        with _lib_zip_scope():
            add = self.__class__(is_import=True)
            add.parent_basedir = self.basedir
            #
            # Only the nest file needs to know about
            # lib name
            #
            if self.lib_name is not None:
                add.lib_name = self.lib_name
            elif lib_name is not None:
                add.lib_name = lib_name
                add.parent_basedir = None

            # add.is_import = True
            errors = add.from_file(filename, root)
            if len(errors)==0:
                for label, node in add.labels.items():
                    if label != "main":
                        self.labels[label] = node
            return errors

    def get_manifest(self):
        """The addon dependency manifest collected during compile: the set of
        `provides` tokens and the list of `requires`/`suggests` declarations.
        Exposed so an offline tool (e.g. `sbs lint`) can read the same data the
        runtime validates - both go through the same collection in compile()."""
        return {"provides": set(self.provides),
                "requires": list(self.requires)}

    def _validate_requirements(self):
        """Order-independent dependency barrier. Run once after the whole story
        (every addon) has compiled, so the `provides` union is complete. An unmet
        `requires` is a hard compile error (blocks the story, surfaces in `sbs
        lint` / `--test` and as a runtime error screen); an unmet `suggests` is a
        logged warning (optional augmentation, keeps running). Runs on the ROOT
        story, whose provides/requires hold the union across all files."""
        errs = []
        logger = logging.getLogger("mast.compile")
        for token, kind, file_name, line_no, line in self.requires:
            if token in self.provides:
                continue
            if kind == "requires":
                # Same shape as compile()'s nested buildErrorMessage (which is not
                # in scope here); the file_name/line pinpoint the declaration.
                errs.append(
                    f"\nError: Unmet dependency: requires '{token}', but no loaded "
                    f"addon provides it. Load the addon that declares 'provides "
                    f"{token}'.\nat {file_name} Line {line_no} - '{line}'\n\n")
            else:  # suggests
                logger.warning(
                    f"{file_name}:{line_no}: suggests '{token}', not provided by any "
                    f"loaded addon (optional - continuing).")
        return errs


    def compile(self, lines, file_name, root):
        # Catching compiler errors lower to give better error message
        errors = []
        # Merge bracket-continued physical lines into one logical line so
        # multiline python expressions parse. Line numbers are preserved.
        # (Comment out the next line to fully disable the feature.)
        lines = join_bracket_continuations(lines)
        try:
            errors = self._compile(lines, file_name, root) or []
        except Exception as e:
            logger = logging.getLogger("mast.compile")
            logger.error(f"Exception: {e}")
            errors.append(f"\nException: {e}")
            errors.append(format_exception("",""))
        # Dev seam: let a harness (cosmos_dev MastVerdict) observe compile errors so a
        # headless --test can FAIL on them. No-op in production (hook is None). Fires
        # per compiled file (incl. imported mastlib files), so a bad addon is caught.
        if errors and Mast.on_compile_error is not None:
            try:
                Mast.on_compile_error(errors, file_name)
            except Exception:
                pass
        return errors

        

    def _compile(self, lines, file_name, root):
        file_num = self.clear(file_name, root)
        line_no = 1 # file line num are 1 based
        
        errors = []
        main = self.labels.get("main")
        if root is not None:
            main = root.labels.get("main", main)
        


        active = main # self.labels.get("main")
        active_name = "main"
        indent_stack = [(0,None)]
        prev_node = None
        label_first_cmd = 0

        # Per-compile block-parsing state. Lives on the local CompileInfo class
        # so every CompileInfo created in this call shares it, and a fresh one is
        # made per compile (no cross-compile / nested-import contamination).
        compile_ctx = CompileContext()

        class CompileInfo:
            ctx = compile_ctx

            def __init__(self) -> None:
                self.indent = None
                self.is_indent = None
                self.is_dedent = None
                self.label = None
                self.prev_node = None
                self.file_num = None
                
        def buildErrorMessage(file_name, line_no, line, error):
            if line != "":
                line = f"- '{line}'"
            basedir = f"module {self.basedir}"
            if self.lib_name is not None:
                basedir = f"addon {self.lib_name}/{self.basedir}"

            return f"\nError: {error}\nat {file_name} Line {line_no} {line}\n{basedir}\n\n"
        
        def buildExceptionMessage(file_name, line_no, line, error):
            if line != "":
                line = f"- '{line}'"
            basedir = f"module {self.basedir}"
            if self.lib_name is not None:
                basedir = f"addon {self.lib_name}/{self.basedir}"
            
            return f"\nException: {error}\nat {file_name} Line {line_no} {line}\n{basedir}\n\n"

        def inject_dedent(ind_level, indent_node, dedent_node, info):
            if len(indent_stack)==0:
                logger = logging.getLogger("mast.compile")
                error = buildErrorMessage(file_name, line_no,"","Indentation Error")
                logger.error(error )
                errors.append(error)
                return
            
            if ind_level < indent_stack[0][0]:
                logger = logging.getLogger("mast.compile")
                error = buildErrorMessage(file_name,line_no,"","Indentation Error")
                logger.error(error )
                errors.append(error)
                return

            if ind_level == indent_stack[0][0]:
                return
            loc = len(self.cmd_stack[-1].cmds)
            end_obj = indent_node.create_end_node(loc, dedent_node, info)
            if end_obj:
                end_obj.line_num = indent_node.line_num
                end_obj.line = indent_node.line
                end_obj.file_num = file_num
                self.cmd_stack[-1].add_child(end_obj)
                
            

        def inject_remaining_dedents():
            nonlocal indent_stack
            l = indent_stack[::-1]
            for (ind_level, ind_obj) in l:
                info = CompileInfo()
                info.indent = ind_level
                info.is_indent = False
                info.is_dedent = True
                info.main = main # self.labels.get("main")
                inject_dedent(ind_level, ind_obj, None, info)
            indent_stack = [(0,None)]


        # Use a position cursor into the full source instead of repeatedly
        # slicing `lines`. Slicing copied the entire remaining file on every
        # token (O(n^2)); match(src, pos) anchors at pos with no copy.
        src = lines
        length = len(src)
        pos = 0
        compile_logger = logging.getLogger("mast.compile")
        debug_enabled = compile_logger.isEnabledFor(logging.DEBUG)
        nodes = self.__class__.nodes
        global _candidate_cache_count
        node_count = len(nodes)
        if _candidate_cache_count != node_count:
            # Node set changed (e.g. an addon registered a node type); rebuild.
            _candidate_cache.clear()
            _candidate_cache_count = node_count
        while pos < length:
            ws = first_non_whitespace_index(src, pos)
            line = 0
            line_no += ws[1]
            pos = ws[0]
            indent = max((ws[0] - ws[2]) - 1, 0)
            #Mast.current_indent = indent  # Replaced with compile_info

            #
            # Allow labels to optionally indent?
            #
            if indent != 0 and active is not None and len(active.cmds) <= label_first_cmd:
                indent_stack = [(indent,None)]

            # Keep location in file
            parsed = False
            #
            # HANDLE END OF FILE
            #
            if pos >= length:
                # Pop out all indents
                inject_remaining_dedents()
                # Let the label generate any commn
                active.generate_label_end_cmds()
                break

            ## 
            # TDO: This has gotten too indented
            #
            try:
                # Only try nodes whose rule can match this line's first char.
                ch = src[pos]
                if len(nodes) != node_count:  # late node registration
                    node_count = len(nodes)
                    _candidate_cache.clear()
                    _candidate_cache_count = node_count
                candidates = _candidate_cache.get(ch)
                if candidates is None:
                    candidates = _candidates_for(nodes, ch)
                    _candidate_cache[ch] = candidates
                for node_cls in candidates:
                    #mo = node_cls.rule.match(lines)
                    mo = node_cls.parse(src, pos)
                    if not mo:
                        continue
                    #span = mo.span()
                    data = mo.data

                    line = src[mo.start:mo.end]
                    pos = mo.end

                    line_no += line.count('\n')


                    parsed = True
                    is_indent = False
                    is_dedent = False

                    if node_cls.__name__ != "Comment":
                        (cur_indent, _)  = indent_stack[-1]
                        if indent > cur_indent:
                            is_indent = True
                            # indent_stack.append(indent)
                        elif indent < cur_indent:
                            is_dedent = True

                    if debug_enabled:
                        compile_logger.debug("PARSED: %s %s", node_cls.__name__, line)



                    #match node_cls.__name__:
                    # Throw comments and markers away
                    if node_cls.__name__ == "Comment":
                        pass
                    elif node_cls.is_label:
                        _info = CompileInfo()
                        data["compile_info"] = _info
                        next = node_cls(**data)
                        next.file_num = file_num
                        next.line_num = line_no
                        #if active.can_fallthrough() and next.can_fallthrough():
                        if active == main:
                            if  root == self and next.can_fallthrough(active):
                                active.next = next
                        elif next.can_fallthrough(active):
                            active.next = next
                        else:
                            active.next = None

                        label_name = next.name

                        existing_label = self.labels.get(label_name) 
                        replace = data.get('replace')
                        if existing_label and not replace:
                            parsed = False
                            error = buildErrorMessage(file_name, line_no, line, f"Duplicate label '{label_name }'. Use 'replace: {data['name']}' if this is intentional.")
                            errors.append(error)
                            break
                        elif existing_label and replace:
                            from .core_nodes.jump_cmd import Jump

                            # Make the pervious version jump to the replacement
                            # making fall through also work
                            existing_label.cmds = [Jump(jump_name=label_name,loc=0)]

                        # Close any remain indents
                        inject_remaining_dedents()
                        # THEN
                        # Generate any close block command
                        active.generate_label_end_cmds()
                        #
                        # A new label starts fresh: drop any await left open by
                        # the previous label (belt-and-suspenders vs unbalanced
                        # blocks).
                        #
                        if len(compile_ctx.await_stack) > 0:
                            compile_ctx.await_stack.clear()
                        ##
                        ##


                        ## Allow label to generate some preabmle commands
                        active = next
                        active_name = label_name
                        active_name = label_name
                        self.labels[active_name] = active
                        _info = CompileInfo()
                        _info.indent = indent
                        _info.is_dedent = is_dedent
                        _info.is_indent = is_indent
                        _info.label = next
                        _info.main = main # self.labels.get("main")
                        next.generate_label_begin_cmds(_info)
                        label_first_cmd = len(next.cmds)
                        
                        self.labels[active_name] = active
                        exists =  Agent.SHARED.get_inventory_value(label_name)
                        exists =  MastGlobals.globals.get(label_name, exists)
                        if exists and not replace:
                            error = buildErrorMessage(file_name,line_no,line,f"Label conflicts with shared name, rename label '{label_name}'.")
                            errors.append(error)
                            break

                        # Sets a variable for the label
                        Agent.SHARED.set_inventory_value(label_name, active)

                        self.cmd_stack.pop()
                        self.cmd_stack.append(active)
                        prev_node = active

                    
                    elif node_cls.__name__== "Import":
                        if indent>0:
                            logger = logging.getLogger("mast.compile")
                            e = "ERROR import cannot be indented or be in conditional"
                            error = buildExceptionMessage(file_name, line_no,line,f"{e}")
                            logger.error(error)
                            errors.append(error)
                            break
                            
                        lib_name = data.get("lib")
                        name = data['name']

                        if name.endswith('.py'):
                            self.import_python_module_for_source(name, lib_name)
                        elif name.endswith('.zip') or name.endswith('.mastlib'):
                            err = self.import_content("__init__.mast", root, name)
                            if err is not None:
                                errors.extend(err)
                                for e in err:
                                    print("import error "+e)
                        else:
                            err = self.import_content(name, root, lib_name)
                            if err is not None:
                                errors.extend(err)
                                for e in err:
                                    print("import error "+e)
                                    return errors
                        prev_node = None

                    elif node_cls.__name__ in ("Provides", "Requires", "Suggests"):
                        # Addon dependency directives. Collected onto the ROOT story
                        # (order-independent union); validated once after the whole
                        # set compiles (see _validate_requirements). No runtime cmd.
                        if indent > 0:
                            errors.append(buildErrorMessage(file_name, line_no, line,
                                f"'{node_cls.__name__.lower()}' must be at top level (column 0)"))
                            break
                        toks = [t.strip() for t in data.get("tokens", "").split(",") if t.strip()]
                        if node_cls.__name__ == "Provides":
                            for t in toks:
                                root.provides.add(t)
                        else:
                            kind = node_cls.__name__.lower()   # "requires" | "suggests"
                            for t in toks:
                                root.requires.append((t, kind, file_name, line_no, line))
                        prev_node = None

                    else:
                        try:
                            loc = len(self.cmd_stack[-1].cmds)
                            info = CompileInfo()
                            info.indent = indent
                            info.is_dedent = is_dedent
                            info.is_indent = is_indent
                            info.label=active
                            info.prev_node = prev_node
                            info.main = self.labels.get("main")
                            info.basedir = root.basedir

                            
                            obj = node_cls(compile_info=info,loc=loc, **data)
                            obj.file_num = file_num
                            obj.line_num = line_no

                        except Exception as e:
                            compile_logger.error(f"Exception: {e}")
                            # Collect and move on: the bad line is already
                            # consumed (pos advanced) and no block state was
                            # mutated, so we can keep compiling and report the
                            # rest of this file's errors in one pass.
                            errors.append(buildExceptionMessage(file_name, line_no,line,f"{e}"))
                            break

                        obj.line = line if Mast.include_code else None
                        base_indent= indent_stack[0][0]
                        if obj.never_indent() and indent>base_indent:
                            errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                            break

                        if not is_indent:
                            if prev_node is not None and prev_node.must_indent():
                                errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                                break
                        if is_indent:
                            if prev_node is None or not prev_node.is_indentable():
                                # prev_node None => indenting under nothing; treat
                                # as bad indentation instead of dereferencing None.
                                if prev_node is None or not prev_node.is_inline_label:
                                    errors.append(buildErrorMessage(file_name,line_no,line,"Bad indentation"))
                                    break
                            block_node = prev_node
                            indent_stack.append((indent,block_node))
                        if is_dedent:
                            if len(indent_stack)==0:
                                errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                                break
                            
                            (i_loc,_) = indent_stack[-1]
                            while i_loc > indent:
                                if len(indent_stack)==1 and obj.is_inline_label:
                                    break

                                (i_loc,i_obj) = indent_stack.pop()
                                if len(indent_stack)==0:
                                    errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                                    return errors # return with first errors

                                # Should equal i_obj
                                end_obj = i_obj.create_end_node(loc, obj,info)
                                #
                                # So far only loops need this
                                # Creates the end node
                                #
                                if end_obj:
                                    self.cmd_stack[-1].add_child(end_obj)
                                    loc+=1
                                    end_obj.file_num = file_num
                                    end_obj.line_num = line_no
                                    end_obj.line = obj.line
                                    obj.loc += 1
                                
                                (i_loc,_) = indent_stack[-1]
                        #
                        # This is for nesting things
                        # like for loops, that should wait to do things 
                        #
                        obj.post_dedent(info)
                        self.cmd_stack[-1].add_child(obj)
                        if not obj.is_virtual():
                            prev_node = obj
                    break
            except Exception as e:
                logger = logging.getLogger("mast.compile")
                error = buildExceptionMessage(file_name, line_no,line,f"{e}")
                logger.error(error)
                logger.error(f"Exception: {e}")

                errors.append(error)
                errors.append(f"\nException: {e}")
                return errors # return with first errors


            if not parsed:
                nn = first_non_newline_index(src, pos)

                if nn > pos:
                    # this just blank lines
                    #line_no += (nn - pos)
                    line = src[pos:nn]
                    pos = nn
                else:
                    nl = first_newline_index(src, pos)
                    bad_line = src[pos:nl]

                    error = buildErrorMessage(file_name, line_no, bad_line,
                                              "Unrecognized syntax; no MAST node matched this line")
                    compile_logger.error(error)
                    errors.append(error)
                    pos = nl + 1

        # (Block-state cleanup that used to live here is no longer needed: that
        # state is now per-compile on compile_ctx and discarded with this call.)
        return errors

    def enable_logging():
        logger = logging.getLogger("mast")
        handler  = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s|%(name)s|%(message)s"))
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        # fh = logging.FileHandler('mast.log')
        # fh.setLevel(logging.DEBUG)
        # logger.addHandler(fh)

