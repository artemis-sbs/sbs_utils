from sbs_utils.agent import Agent
from sbs_utils.mast.core_nodes.comment import Comment
from sbs_utils.mast.mast import CompileContext
from sbs_utils.mast.mast import ExpParseData
from sbs_utils.mast.mast import InlineData
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import Rule
from sbs_utils.mast.mast import SourceMapData
from enum import Enum
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.core_nodes.inline_label import InlineLabel
from sbs_utils.mast.core_nodes.label import Label
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import Scope
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
from pathlib import Path
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.futures import Waiter
from zipfile import ZipFile
from functools import partial
def DEBUG (msg):
    ...
def _describe_expr_values (code):
    """`name = type: repr` for each name a failing expression referenced, or "".
    
    A MAST runtime error quotes the source line and stops there, which is one step short
    of useful: `link(p, "extra_scan_source", o)` says nothing about what `p` WAS, and
    every "where did that value come from" hunt starts by trying to find out. This is
    what identified the loop-iterator leak - the log showed `p` holding a dict from a
    completely different collection while `o`, iterating the very same list one line
    above, held a correct id. That asymmetry is the whole diagnosis, and it is invisible
    without the values.
    
    co_names is what the compiler recorded for this expression, so only names the line
    really uses are printed. Callables are skipped - the procedural function being called
    is never the surprise."""
def _safe_for_gui (text):
    """Make a repr safe to put in front of the engine.
    
    This block ends up in an ErrorPage, so it is engine-rendered text, and the values in
    it are arbitrary mission data - a ship name, a loaded YAML row, whatever the author
    put in a variable. Two things in there are not the engine's friends:
    
      * NON-ASCII. Engine-rendered strings are ASCII only; a name with a curly quote or an
        accent has no business reaching a GUI string through a diagnostic.
      * `^`, which is a GUI style SEPARATOR. handlerhooks already strips it from the
        hook-level error text (`text_err.replace(chr(94), "")`), but the MAST-level path
        does not - so before this, a caret inside a repr went straight through.
    
    Neither was reachable before values were printed here; adding the values added the
    exposure, so the sanitising belongs with it."""
def close_lib_zips ():
    """Drop every cached .mastlib handle. Safe to call at any time; the next read
    reopens."""
def describe_eval_failure (code):
    """Header describing the live exception for a MAST eval/exec failure.
    
    Called from inside an ``except`` block, so ``sys.exc_info()`` is still live.
    Names the exception TYPE (a bare message hides whether it was a NameError or
    a TypeError), quotes the MAST expression the code object came from, and adds
    a hint for the scope-keyword trap."""
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
def get_fall_through (inner):
    ...
def get_task_id ():
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
def mast_expr_source (code):
    """The MAST source text a code object was compiled from, or None.
    
    ``eval``/``exec`` also accept a raw string (a few nodes build one on the
    fly), in which case the source IS the argument."""
def profile_dropped_addons ():
    """Addon folder names the active profile removed from this compile."""
class ChangeRuntimeNode(MastRuntimeNode):
    """class ChangeRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node):
        ...
    def poll (self, mast: 'Mast', task: 'MastAsyncTask', node):
        ...
    def test (self):
        ...
class MastAsyncTask(Agent, Promise):
    """class MastAsyncTask"""
    def __init__ (self, main: "'MastScheduler'", inputs=None, name=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    @property
    def active_label (self):
        ...
    @property
    def active_label_object (self):
        ...
    def add_dependency (id, task):
        ...
    def add_role (self, role: 'str'):
        """Tagging a task makes it a discoverable RECORD, not just execution.
        
        procedural/prefab.py sets `prefab = FrameContext.task`, so a prefab IS its
        task: `prefab_torpedo_type` runs once and then tags itself
        ('torpedo_definition' + the torpedo key) so docking can resolve the type
        long after the label finished. Such a task must (a) survive disposal and
        (b) be findable by inventory key like any other agent - so joining the
        has_inventory index is backfilled here, once, rather than paid by every
        short-lived route/comms task that will never be looked up."""
    def are_variables_defined (self, keys):
        """Check if the provided variable keys are defined in this task.
        Args:
            keys (str): A comma-separated list of the keys.
        Returns:
            bool: True if all variables are defined, otherwise False."""
    def cancel (self, msg=None):
        ...
    def clear ():
        ...
    def compile_and_format_string (self, value):
        ...
    def dispose (self):
        """Drop a FINISHED task from the Agent registries.
        
        A task is an Agent: __init__ calls self.add(), which registers it in
        Agent.all, in Agent.roles under __MAST_TASK__, and in Agent._has_inventory
        under EVERY variable name it holds (start_task(inherit=True) copies the
        whole parent scope, so that is a lot of names).  Dropping the task from the
        scheduler's `tasks` list left all of that behind, so a busy mission grew
        Agent.all without bound -- ~150 dead tasks a sim-second on LM, 47k agents
        of which 92% were finished tasks.
        
        Idempotent, and safe to call while the task object is still referenced:
        this only unregisters the id, it does not invalidate live references
        (`mast_task`, an awaited promise's result).  A task that is later revived
        via jump_restart_task re-registers itself there."""
    def emit_signal (self, name, sender_task, label_info, data):
        ...
    def end (self):
        ...
    def eval_code (self, code, end_on_exception=True):
        """Backward-compatible wrapper: a failed expression still returns None.
        
        Kept so every existing caller (including mission code) behaves exactly as
        before. Library nodes use eval_code_checked so they can stop instead."""
    def eval_code_checked (self, code, end_on_exception=True):
        """Evaluate a MAST expression, returning EVAL_ERROR if it raised.
        
        Prefer this over ``eval_code`` anywhere the VALUE is used: ``None`` is a
        legal MAST value, so it cannot carry "this blew up" - see EVAL_ERROR."""
    def eval_globals (self):
        """Globals for an expression: builtins plus this story's LABEL names.
        
        Labels used to live in Agent.SHARED, i.e. in the variable namespace, which is how
        `watcher = 0` destroyed `=== watcher` (LM #544). As globals they still resolve --
        `task_schedule(watcher)` works -- but a write can never land on one, and a task
        variable of the same name shadows it for reads, which is the sane reading.
        
        Falls back to the module constant when no story is reachable (bare-scheduler
        tests, and any caller that predates a compiled Mast)."""
    def exec_code (self, code, vars, gbls):
        ...
    def format_string (self, message):
        ...
    def get (id):
        ...
    def get_active_node (self):
        ...
    def get_active_node_source_map (self):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def get_runtime_error_info (self, rte):
        ...
    def get_scoped_value (self, key, defa, scope):
        ...
    def get_shared_variable (self, key, default=None):
        ...
    def get_symbols (self):
        ...
    def get_value (self, key, defa=None):
        ...
    def get_variable (self, key, default=None):
        ...
    def gui_host_task (self):
        """The page's GUI task, when this task is not it. Else None."""
    def handler_defaults_to_sub_task ():
        """Whether an unspecified on_press=<label> runs as a sub-task."""
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def is_data_record (self):
        """True when this task has been tagged for DISCOVERY, so it must outlive
        its own execution.
        
        A MastAsyncTask is an Agent, and missions legitimately use one as a
        persistent data record: the label runs once to populate it, then tags it
        with roles so other code can find it later. LegendaryMissions registers
        every torpedo type this way (`prefab_torpedo_type` -> roles
        'torpedo_definition' + 'homing'/'nuke'/'beacon'/...), and docking's rearm
        step resolves the type through that role set long after the task ended.
        Disposing such a task deletes the registry.
        
        A role beyond the built-in __mast_task__ is the signal: nothing adds one
        unless it intends the task to be found."""
    @property
    def is_observable (self):
        ...
    def jump (self, label='main', activate_cmd=0, respect_inline=False):
        ...
    def jump_in_label (self, label, activate_cmd=0):
        """Intra-label pointer move for loop control flow. See MastTicker."""
    def jump_restart_task (self, label='main', activate_cmd=0):
        """Used by the mission runner to run multiple labels"""
    def poll (self):
        ...
    def pop_label (self, inc_loc=True, true_pop=False):
        ...
    def purge_inline_signals (self):
        """Unregister the handlers owned by the build that is being replaced.
        
        Called from StoryPage.on_new_gui, at the same moment the wholesale purge
        used to run. The build now under construction has its registrations in
        pending_inline_signals, so they survive this -- which is the whole of the
        #589 fix. Idempotent: safe if the swap already ran."""
    def push_inline_block (self, label, activate_cmd=0, data=None):
        ...
    def push_label (self, label, activate_cmd=0, data=None):
        ...
    def queue_inline_signal (self, name, info):
        ...
    def queue_on_change (self, runtime_node):
        ...
    def remove_all_sub_tasks (self):
        ...
    def remove_id (id):
        ...
    def remove_sub_task (self, t):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def revive_for_handler (self, host=None):
        """Wake a task that ENDED NORMALLY so a GUI handler it registered can run.
        
        A widget's handler is owned by the task that BUILT the widget: an
        `on gui_message(w):` block is an inline block in that task's label, and
        `on_press=<label>` is a jump on that task. When the builder was
        scheduled and then ended (->END / yield success) the handler had no way
        to run at all -- push_inline_block only queues pending_jump, and tick()
        returns at its leading `if self.done:` before ever reading it. The click
        was discarded silently. See LM issue #707.
        
        Returns True when the task is runnable afterwards.
        
        Reviving in place rather than spawning a fresh task keeps the builder's
        own scope, active_label and identity, so the block still closes over the
        locals its author wrote it against -- and, with the inline block pop
        fixed, the woken task pops back to its own ->END and finishes again.
        
        `host` is the task that will TICK the revived one (the page's gui_task),
        so a handler that awaits still gets ticks. It is a ticking parent only:
        is_sub_task/root_task are deliberately left alone, because changing them
        would change variable scoping."""
    def run_on_change (self):
        ...
    def runtime_error (self, msg):
        ...
    def set_shared_variable (self, key, value):
        ...
    def set_value (self, key, value, scope):
        ...
    def set_value_keep_scope (self, key, value):
        ...
    def set_variable (self, key, value):
        ...
    def start_sub_task (self, label='main', inputs=None, task_name=None, defer=False, active_cmd=0) -> 'MastAsyncTask':
        ...
    def start_task (self, label='main', inputs=None, task_name=None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
        ...
    def stop_for_dependency (id):
        ...
    def swap_inline_signals (self):
        """Promote this build's registrations, at present time."""
    def swap_on_change (self):
        ...
    def sweep_finished ():
        """Backstop: dispose any FINISHED task still sitting in the registries.
        
        Disposing at the two points where a task leaves `tasks` / `sub_tasks`
        catches the common case, but tasks are started from a dozen places
        (routes, comms, science, overlays) and some run to completion outside
        those lists -- notably a sub-task whose parent never ticks again, which
        leaves it done-but-registered forever. This sweep is creation-site
        agnostic: if it is done, it does not belong in the registries.
        
        Cheap: it walks the __mast_task__ role set, not all of Agent.all, and
        runs on the GarbageCollector cadence rather than every frame. dispose()
        is idempotent, and a task revived later by jump_restart_task re-registers."""
    def tick (self):
        ...
    def tick_in_context (self):
        ...
    @property
    def tick_result (self):
        ...
    def tick_subtasks (self):
        ...
class MastScheduler(Agent):
    """class MastScheduler"""
    def __init__ (self, mast: 'Mast', overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def _start_task (self, label='main', inputs=None, task_name=None) -> 'MastAsyncTask':
        ...
    def cancel_task (self, name):
        ...
    def clear ():
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_inventory_value (self, collection_name, default=None):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def get_seconds (self, clock):
        """Gets time for a given clock default is just system """
    def get_symbols (self):
        ...
    def get_value (self, key, defa=None):
        """MastStoryScheduler completely overrided this so changes here should go there"""
    def get_variable (self, key, defa=None):
        ...
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def is_running (self):
        ...
    def is_server (self):
        ...
    def on_start_task (self, t):
        ...
    def remove_id (id):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def runtime_error (self, message):
        ...
    def schedule (self, task):
        ...
    def set_inventory_value (self, collection_name, value):
        ...
    def set_value (self, key, value, scope):
        ...
    def set_variable (self, key):
        ...
    def start_task (self, label='main', inputs=None, task_name=None, defer=False, unscheduled=False, loc=0) -> 'MastAsyncTask':
        ...
    def tick (self):
        ...
class MastTicker(object):
    """Interpreter for one task's compiled `.mast` (BASIC-like linear flow).
    
    State
    -----
    - ``active_label`` / ``active_cmd`` / ``cmds`` — the current label name, the
      index of the current command within it, and that label's command list.
    - ``runtime_node`` — the live runtime instance for the current command
      (built in ``next()`` via ``enter()``, retired via ``leave()``).
    - ``last_poll_result`` — the most recent ``PollResults`` (drives the caller).
    - ``done`` — task finished.
    
    Control transfer is *deferred*: methods set ``pending_jump`` /
    ``pending_pop``, and ``tick()`` applies them at the top of its loop.
    **``pending_jump`` always wins over ``pending_pop``.**
    
    - ``jump(label, cmd)`` — request a jump (sets ``pending_jump``). A jump also
      unwinds any outstanding inline-block frames (see ``pop_on_jump``), because
      jumping out of an inline context abandons it.
    - ``do_jump(...)`` — performs the jump: resolves the target (label name,
      sub/inline label, or runtime node), repoints ``cmds`` /
      ``active_label`` / ``active_cmd``, then ``next()``.
    - ``do_resume(...)`` — re-enters a *saved* ``runtime_node`` (used when an
      inline block pops back to resume the very node that pushed it).
    
    label_stack (a list of ``PushData``) has two push styles:
    - ``push_label`` — a true "call": saves ``(active_label, active_cmd)`` and
      jumps; the matching ``pop_label`` returns to ``active_cmd + 1``.
    - ``push_inline_block`` — for buttons / dropdowns / event routes that run a
      block and then **resume the same runtime node** that was active when they
      fired. It saves the node too and bumps ``pop_on_jump``.
    
    ``pop_on_jump`` counts inline-block frames that must be auto-unwound the next
    time we ``jump`` (a jump escapes the inline context). ``pop_label`` chooses
    between resuming the saved node (``do_resume``) and treating the pop like a
    jump back to the caller's next command."""
    def __init__ (self, task, main):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def call_leave (self):
        ...
    def do_jump (self, label='main', activate_cmd=0):
        ...
    def do_resume (self, label, activate_cmd, runtime_node):
        ...
    def end (self):
        ...
    def get_active_node (self):
        ...
    def get_runtime_error_info (self, rte):
        ...
    def jump (self, label='main', activate_cmd=0):
        ...
    def jump_in_label (self, label, activate_cmd=0):
        """Move the instruction pointer WITHIN the current label. Not a jump.
        
        A `for`/`while` loop implements iteration by moving the pointer back to
        its own start and, when it finishes, forward to its dedent - both inside
        one label. That is not leaving anywhere, but it used to go through
        `jump()`, which unwinds `pop_on_jump` "to get back to the main flow" and
        so POPPED the enclosing inline block off `label_stack`.
        
        An inline block is how a widget handler runs, and its `data=` lives on
        that stack entry, so a single loop anywhere in an `on gui_message` block
        silently deleted every injected variable from the loop onward:
        
            fab_btn = gui_button("Build", data={"rk": key, "rnames": names})
            on gui_message(fab_btn):
                for n in rnames:      # <- reads fine, then eats the block
                    ...
                signal_emit("build", {"recipe": rk})   # NameError: 'rk'
        
        Reported from LegendaryMissions' Fabricator (beacon_tabs.mast), where
        the Build button could not build anything. An EMPTY loop did it too, so
        "it only breaks with items" was not even a clue. The `cosmos-gui` skill
        recommends `data=` as the reliable escape from the OTHER for-loop trap
        (handlers registered inside a loop), which walked straight into this one.
        
        Worse than the lost variables: the pop left the stack one entry short,
        so when the block ended `pop_label` took an entry belonging to whoever
        pushed before it."""
    def next (self):
        ...
    def pop_label (self, inc_loc=True, true_pop=False):
        ...
    def push_inline_block (self, label, activate_cmd=0, data=None):
        ...
    def push_label (self, label, activate_cmd=0, data=None):
        ...
    def runtime_error (self, rte):
        ...
    def tick (self):
        ...
class PushData(object):
    """class PushData"""
    def __init__ (self, label, active_cmd, data=None, resume_node=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class PyTicker(object):
    """class PyTicker"""
    def __init__ (self, task) -> 'None':
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def active_label (self):
        ...
    def do_jump (self):
        ...
    def end (self):
        ...
    def get_active_node (self):
        ...
    def get_gen (self, label):
        ...
    def get_runtime_error_info (self, rte):
        ...
    def jump (self, label):
        ...
    def pop (self):
        ...
    def pop_label (self, inc_loc=True, true_pop=False):
        ...
    def push (self, label):
        ...
    def push_inline_block (self, label, _loc=0, data=None):
        ...
    def quick_push (self, func):
        ...
    def runtime_error (self, rte):
        ...
    def tick (self):
        ...
