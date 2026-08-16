from sbs_utils.agent import Agent
from sbs_utils.mast.core_nodes.comment import Comment
from enum import Enum
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import Scope
from pathlib import Path
from zipfile import ZipFile
def DEBUG (msg):
    ...
def _candidates_for (nodes, ch):
    ...
def _node_first_chars (node_cls):
    ...
def _open_lib_zip (lib_name):
    ...
def close_lib_zips ():
    """Drop every cached .mastlib handle. Safe to call at any time; the next read
    reopens."""
def find_exp_end (s, expect_block):
    ...
def first_chars_for_pattern (pattern):
    """Return a set of possible first chars, or None for 'matches anything'."""
def first_newline_index (s, start=0):
    ...
def first_non_newline_index (s, start=0):
    ...
def first_non_space_index (s):
    ...
def first_non_whitespace_index (s, start=0):
    ...
def format_exception (message, source):
    ...
def join_bracket_continuations (src):
    """Merge bracket-continued physical lines into one logical line.
    
    Slice-copying scanner: the state machine below only ever stops at a character
    that can change state (``_NEXT``), at a verbatim region's closer (``str.find``),
    or at a string's escape/closer (``_IN_STR``). Every inert run between two stops
    is appended as ONE slice. The previous character-at-a-time version appended one
    element per byte and re-probed ``startswith`` at every position, which made this
    pre-pass the single largest cost in compiling a big story (measured: 232ms of
    LegendaryMissions' ~1s compile, 57 of its 171 files). Output is byte-identical."""
class CompileContext(object):
    """Per-compile scratch state for block-structured nodes.
    
    if/match/await/on/for nodes need to track their open blocks while parsing.
    This state used to live as class attributes on the node types and was shared
    across every compile, so an aborted compile (we bail early on the first
    error) or a nested import (imports compile recursively mid-parse) could
    corrupt the next/outer compile -- e.g. `if_chains` keyed only by indent could
    alias unrelated blocks. Each `_compile` now gets its own context, reached by
    nodes through `compile_info.ctx`."""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
class ExpParseData(object):
    """class ExpParseData"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def in_something (self):
        ...
    @property
    def is_valid (self):
        ...
class InlineData(object):
    """class InlineData"""
    def __init__ (self, start, end):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Mast(object):
    """class Mast"""
    def __init__ (self, cmds=None, is_import=False):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _compile (self, lines, file_name, root):
        ...
    def _from_file (self, file_name, root):
        """Docstring"""
    def _validate_label_names (self):
        """Order-independent guard: an assignment must not take a label's name.
        
        `watcher = 0` alongside `=== watcher` used to DESTROY the label -- it lived in
        Agent.SHARED, so the assign resolved to Scope.SHARED and overwrote it for every
        task. Labels now have their own namespace, so the write only shadows; but a
        shadow still means `task_schedule(watcher)` in that task gets 0 and dies in
        do_jump with `AttributeError: 'int' object has no attribute 'name'`, pointing at
        neither the label nor the assignment. Name it here instead. (LM #544)
        
        Runs at the same hook as _validate_requirements, where the label table holds
        every label in the story -- so it does not matter whether the label compiled
        before the assignment, or in a different addon entirely."""
    def _validate_requirements (self):
        """Order-independent dependency barrier. Run once after the whole story
        (every addon) has compiled, so the `provides` union is complete. An unmet
        `requires` is a hard compile error (blocks the story, surfaces in `sbs
        lint` / `--test` and as a runtime error screen); an unmet `suggests` is a
        logged warning (optional augmentation, keeps running). Runs on the ROOT
        story, whose provides/requires hold the union across all files."""
    def add_scheduler (self, scheduler):
        ...
    def addon_source_folder (mission_dir, lib_name):
        """The mission-local source folder for a declared mastlib, or None.
        
        A lib is named ``{user}.{repo}.{folder}.{version}.{ext}``, so the addon folder is
        the third dot-segment. Answers None unless that folder holds an ``__init__.mast`` -
        the same test find_imports uses to call something an addon, so a mission that
        merely happens to have a same-named folder cannot suppress a lib it needs."""
    def clear (self, file_name, root):
        ...
    def compile (self, lines, file_name, root):
        ...
    def content_from_lib_or_file (self, file_name):
        ...
    def enable_logging ():
        ...
    @property
    def eval_globals (self):
        """The globals dict every MAST expression is eval'd against.
        
        `{"__builtins__": MastGlobals.globals}` plus this story's label names. Python
        resolves a bare name locals -> globals -> builtins, so putting labels here gives
        them exactly the precedence they should have: `task_schedule(watcher)` resolves,
        and a task variable of the same name shadows it for reads.
        
        Built ONCE and cached, because eval_code runs on every expression in the game --
        merging the label table per eval would put a dict build of every label in the
        story on the hottest path there is. The builtins entry holds a REFERENCE to
        MastGlobals.globals, so functions registered later are still visible."""
    def expand_resources (self):
        ...
    def find_add_ons (self):
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
        that __lib__ had already made unnecessary."""
    def find_imports (self, folder):
        ...
    def from_file (self, file_name, root):
        """Compile `file_name` and everything it pulls in.
        
        `root is None` means this is the ROOT compile of a story; nested imports
        pass the root through. The scope guard owns the .mastlib handle cache for
        the outermost compile only."""
    def get_manifest (self):
        """The addon dependency manifest collected during compile: the set of
        `provides` tokens and the list of `requires`/`suggests` declarations.
        Exposed so an offline tool (e.g. `sbs lint`) can read the same data the
        runtime validates - both go through the same collection in compile()."""
    def get_source_file_name (file_num):
        ...
    def import_content (self, filename, root, lib_name):
        ...
    def import_python_module_for_source (self, name, lib_name):
        ...
    def make_global (func):
        ...
    def make_global_var (name, value):
        ...
    def prune_main (self):
        ...
    def refresh_schedulers (self, source, label):
        """TODO: Deprecate for signals?
        
        Args:
            source (_type_): _description_
            label (_type_): _description_"""
    def remove_scheduler (self, scheduler):
        ...
    def signal_emit (self, name, sender_task, data):
        ...
    def signal_register (self, name, task, label_info):
        ...
    def signal_unregister (self, name, task):
        ...
    def signal_unregister_all (self, task):
        ...
    def signal_unregister_all_inline (self, task):
        ...
    def signal_unregister_info (self, name, task, info):
        """Drop ONE registration, by identity.
        
        `signal_unregister_all_inline` removes every inline handler a task owns,
        which is too blunt once a task holds handlers from two different GUI
        builds at the same time -- the moment the new build starts, its already
        registered `on signal` blocks are indistinguishable from the old build's
        (LM #589). Removing the exact SignalLabelInfo the caller is tracking keeps
        the two apart."""
    def update_shared_props_by_tag (self, tag, props, test):
        ...
class Rule(object):
    """class Rule"""
    def __init__ (self, re, cls):
        """Initialize self.  See help(type(self)) for accurate signature."""
class SourceMapData(object):
    """class SourceMapData"""
    def __init__ (self, file_name, basedir):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
class _lib_zip_scope(object):
    """Own the .mastlib handle cache for the OUTERMOST compile, whichever public
    entry point that is. Nested calls ride the same cache; the outermost one closes
    it on the way out, including on exceptions.
    
    Depth-counted rather than keyed on `root is None`, because import_content() is
    a legitimate standalone entry (tooling and tests call it with a non-None root).
    Keying on root leaked a handle there and left a Windows lock on the .mastlib -
    the caller then could not delete or rebuild it."""
    def __enter__ (self):
        ...
    def __exit__ (self, *exc):
        ...
