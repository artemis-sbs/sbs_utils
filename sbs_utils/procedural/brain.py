""" Manage all brains
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value, has_inventory
from sbs_utils.agent import Agent
from sbs_utils.procedural.query import (to_set, to_object, to_client_object, object_exists,
                                        is_space_object_id, is_grid_object_id)
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.tickdispatcher import TickDispatcher, RollingSlicer
import random

from enum import IntFlag


#__brain_tick_task = None
def brain_schedule():
    """Schedule the brain tick task via the objective system."""
    from .objective import objective_schedule
    objective_schedule()
    # This is handled in Objectives NOW
    #
    # Schedule a simple tick task 
    #
    # global __brain_tick_task
    # if __brain_tick_task is None:
    #     __brain_tick_task = TickDispatcher.do_interval(brains_run_all, 3)

class BrainType(IntFlag):
    # Alters result
    Invert = 0x02
    AlwayFail = 0x04
    AlwaySuccess = 0x08
    #
    Simple = 0x100
    Sequence = 0x200
    Select = 0x400


class Brain:
    # label -> True once we have complained about it. A leaf that does not end properly
    # would otherwise print on every pass, for every agent, forever.
    _warned_leaf = {}

    def __init__(self, agent, label, data, client_id, brain_type=BrainType.Simple):
        super().__init__()
        self.agent = agent
        self.label = label #Label could have metadata
        self.data = data
        self._started = False
        self._result = PollResults.OK_IDLE
        self._active = None
        # Ability to have console/client based brains
        self.client_id = client_id
        self.brain_type = brain_type
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    
    @property
    def active(self):
        if self.brain_type & BrainType.Simple:
            if self.label is not None:
                return self.label.name
        elif self._active is not None:
            return self._active.active
        return "idle"

    @property
    def active_desc(self):
        if self.brain_type & BrainType.Simple:
            if self.label is not None:
                desc = self.label.name
                desc = self.label.get_inventory_value("desc", desc)
                if not isinstance(desc, str) and isinstance(desc, list):
                    desc = random.choice(desc)

                desc = self.label.get_inventory_value("DisplayName", desc)
                return desc
        elif self._active is not None:
            return self._active.active_desc
        return "idle"

    ### Brains are never Done
    # @property
    # def done(self):
    #     #return self._done
    #     return False
    
    # @done.setter
    # def done(self, _done):
    #     self._done = _done
    
    @property
    def result(self):
        return self._result
    
    @result.setter
    def result(self, res):
        if self.brain_type & BrainType.AlwayFail:
            res = PollResults.BT_FAIL
        elif self.brain_type & BrainType.AlwaySuccess:
            res = PollResults.BT_SUCCESS
        elif self.brain_type & BrainType.Invert:
            if res == PollResults.BT_FAIL:
                res  = PollResults.BT_SUCCESS
            elif res == PollResults.BT_SUCCESS:
                res  = PollResults.BT_FAIL

        self._result = res

    def run(self):
        match self.brain_type&0xFF00:
            case BrainType.Simple:
                self.run_simple()
            case BrainType.Sequence:
                self.run_sequence()
            case BrainType.Select:
                self.run_select()

    def run_select(self):
        # Select runs until a success
        # Otherwise it fails
        self._active = None
        self.result =  PollResults.BT_FAIL
        for child in self.children:
            child.result = PollResults.OK_IDLE
        for child in self.children:
            child.run()
            if child.result == PollResults.BT_SUCCESS:
                self.result =  PollResults.BT_SUCCESS
                self._active = child
                set_inventory_value(self.agent, "brain_active", child.active_desc)
                return
        self.result =  PollResults.BT_FAIL

    def run_sequence(self):
        # Sequence needs all to succeed
        # Otherwise it fails
        for child in self.children:
            child.result = PollResults.OK_IDLE
        for child in self.children:
            child.run()
            if child.result == PollResults.BT_FAIL:
                self.result =  PollResults.BT_FAIL
                return
        
        self.result =  PollResults.BT_SUCCESS



    def run_simple(self):
        # Convert label string to label object
        if isinstance(self.label, str):
            task = get_inventory_value(self.client_id, "GUI_TASK", FrameContext.task)    
            self.label = task.main.mast.labels.get(self.label, None)
        if not self._started:
            self._started = True
            enter = self.label.labels.get("enter")
            if enter is not None:
                self.run_sub_label(enter.loc+1)
            
        test = self.label.labels.get("test",None)
        if test is not None:
            self.result = self.run_sub_label(test.loc+1)
        else:
            self.result = self.run_sub_label(0)


    def run_sub_label(self, loc):
        task = get_inventory_value(self.client_id, "GUI_TASK", FrameContext.task)
        t : MastAsyncTask
        t = task.start_task(self.label, self.data, defer=True, inherit=False)
        t.jump(self.label, loc)
        t.set_variable("BRAIN", self)
        #t.set_variable("BRAIN_ID", self.id)
        # `or to_client_object` so BRAIN_AGENT agrees with BRAIN_AGENT_ID. brain_add(0,
        # ...) writes through to_agent_list and the tick loop resolves with Agent.get, so
        # a brain on the SERVER console really runs - but to_object refuses id 0, so the
        # body saw BRAIN_AGENT None while BRAIN_AGENT_ID said 0.
        t.set_variable("BRAIN_AGENT", to_object(self.agent) or to_client_object(self.agent))
        t.set_variable("BRAIN_AGENT_ID", self.agent)
        t.tick_in_context()
        res = t.tick_result
        # A LEAF THAT DID NOT FINISH MUST BE ENDED, or it never will be.
        #
        # `yield success` / `yield fail` resolve to OK_END / FAIL_END, which mark the task
        # done and let the scheduler dispose of it. Anything else - `await` (OK_RUN_AGAIN)
        # or `yield idle` (OK_IDLE) - leaves a live task appended to the scheduler, ticked
        # every frame forever. The brain then starts ANOTHER one next pass, so an awaiting
        # leaf leaked one immortal task every pass for the life of the mission.
        #
        # It also read as not-success, so a Select silently fell through to the next
        # sibling: the leaf appeared to do nothing while quietly multiplying. `Objective`
        # has always ended its non-terminal leaves (objective.py); brains never did.
        #
        # Nothing shipped relies on the old behaviour - no brain-typed label in any
        # mission awaits or yields idle (the `await`s nearby live in ordinary `==` task
        # labels, which is the correct place for work that takes time).
        if res not in (PollResults.BT_SUCCESS, PollResults.BT_FAIL):
            t.end()
            if not Brain._warned_leaf.get(self.label):
                Brain._warned_leaf[self.label] = True
                name = getattr(self.label, "name", self.label)
                print(f"brain leaf '{name}' did not end in yield success/fail "
                      f"(got {res}); it was ended to stop it leaking a task per pass. "
                      f"Long work belongs in a task_schedule'd label gated by a flag.")
        return res
        


            

def brain_clear(agent_id_or_set):
    """Remove the behaviour-tree brain from one or more agents.

    Clears the ``__BRAIN__`` inventory key so the agent's brain stops running
    on the next tick. Does not explicitly stop any sub-tasks already started
    by brain labels.

    Args:
        agent_id_or_set: Agent ID, object, or set/list of either.

    Example:
        brain_clear(ENEMY_ID)
    """
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        set_inventory_value(agent, "__BRAIN__", None)


def brain_pause(agent_id_or_set, paused=True):
    """Pause (or resume) one or more agents' brains without removing them.

    A paused brain is skipped by ``brains_run_all`` until resumed - used when an
    object is parked on the standby list so its brain doesn't act on a
    non-simulated object. The brain tree is preserved (unlike ``brain_clear``).

    Args:
        agent_id_or_set: Agent ID, object, or set/list of either.
        paused (bool, optional): True to pause, False to resume. Defaults True.
    """
    for agent in to_set(agent_id_or_set):
        set_inventory_value(agent, "__BRAIN_PAUSED__", paused)


def brain_resume(agent_id_or_set):
    """Resume one or more agents' brains (see ``brain_pause``)."""
    brain_pause(agent_id_or_set, False)


def brain_add_parent(parent, agent, label, data=None, client_id=0):
    """Add one or more brain nodes as children of an existing brain node.

    Handles plain labels, strings, lists (multiple siblings), and structured
    dicts (``{"SEL_name": [...]}`` or ``{"SEQ_name": [...]}``) recursively.

    Args:
        parent (Brain): Parent brain node to attach children to.
        agent (int): Agent ID owning the brain.
        label (label | str | list | dict): Brain node specification.
        data (dict, optional): Variables passed to child tasks. Defaults to
            None.
        client_id (int, optional): Client context for GUI-task resolution.
            Defaults to 0 (server).
    """
    if isinstance(label, str):
        label = label.strip()

    if isinstance(label, str):
        task = FrameContext.task
        l = label
        label = task.main.mast.labels.get(label, None)
        if label is None:
            print(f"Ignoring brain configured with invalid label {l}")
            return
        
        child = Brain(agent, label, data, client_id, BrainType.Simple)
        parent.add_child(child)
        return
        
    if isinstance(label, MastNode):
        child = Brain(agent, label, data, client_id, BrainType.Simple)
        parent.add_child(child)
        return
        
        
    if isinstance(label, list):
        for l in label:
            # Carry `data` and `client_id` down. They used to be dropped here, so every
            # child of a bare list silently fell back to client_id 0 (the server) and lost
            # its data dict - while the dict forms below passed both correctly.
            brain_add_parent(parent, agent, l, data, client_id)
        return

    if isinstance(label, dict):
        keys = label.keys()
        length = len(keys)
        sel = None
        seq = None
        # Keep what was handed down; a child that does not name its own `data` inherits
        # it. Blanking it here is what made the fallback below unreachable.
        inherited_data = data
        data = None
        the_label = None
        if length == 1:
            test = list(keys)[0]
            if test.startswith("SEQ"):
                seq = label.get(test)
                the_label = test    
            elif test.startswith("SEL"):
                sel = label.get(test)
                the_label = test

        if sel is None and seq is None:
            # FALL BACK to the data handed down, rather than nulling it. A child written
            # as {"label": x} says nothing about data, so it should inherit what the
            # caller passed; only {"label": x, "data": {...}} means "use mine instead".
            # Reading it unconditionally meant a bare-label sibling and a dict sibling in
            # the same list got different data for no stated reason.
            data = label.get("data", inherited_data)
            the_label = label.get("label")
        
        
        if sel is not None:
            child = Brain(agent, the_label, None, client_id, BrainType.Select)
            parent.add_child(child)
            brain_add_parent(child, agent, sel, None, client_id)
        elif seq is not None:
            child = Brain(agent, the_label, None, client_id, BrainType.Sequence)
            parent.add_child(child)
            brain_add_parent(child, agent, seq, None, client_id)
        elif the_label is not None:
            brain_add_parent(parent, agent, the_label, data, client_id)


def brain_add(agent_id_or_set, label, data=None, client_id=0, parent=None,
              root_type=BrainType.Select):
    """Add a behaviour-tree node to one or more agents.

    Creates or extends the agent's brain tree. The root is a **Select** node
    (runs children in order, stops at first success). Labels can be plain
    label references, strings, or structured dicts/lists for nested trees.

    Structured dict forms:
    - ``{"label": my_label, "data": {...}}`` — simple node with data
    - ``{"SEL_name": [child1, child2]}`` — Select composite node
    - ``{"SEQ_name": [child1, child2]}`` — Sequence composite node

    A list of labels adds multiple sibling nodes under the parent.

    Args:
        agent_id_or_set: Agent ID, object, or set/list of either.
        label (label | str | dict | list): Behaviour node(s) to add.
        data (dict, optional): Variables passed when the label runs. Defaults
            to None.
        client_id (int, optional): Client context for GUI-task resolution.
            Defaults to 0 (server).
        parent (Brain | None, optional): Parent node to attach to. Defaults to
            None (attaches to the agent's root node, creating it if needed).
        root_type (BrainType, optional): Composite type for the root when this call
            CREATES it. Defaults to ``BrainType.Select`` - children run in priority
            order and the first success wins, which is what a behaviour list wants.
            Pass ``BrainType.Sequence`` when every child should run each pass (e.g. a
            set of independent per-console jobs, where a Select would let the first
            success starve the rest). Ignored when the agent already has a root, so a
            later call can never silently re-type an existing tree.

    Example:
        brain_add(ENEMY_ID, patrol_label)
        brain_add(ENEMY_ID, {"SEL_combat": [attack_label, evade_label]})
    """
    brain_schedule()
    agent_id_or_set = to_set(agent_id_or_set)
    for agent in agent_id_or_set:
        # RESOLVE INTO A LOCAL, never back into `parent`. `parent` is this function's
        # parameter, so writing to it leaked the first agent's root into every later
        # iteration: agents 2..N were attached as children of agent #1's tree and never
        # got a `__BRAIN__` entry of their own. `has_inventory("__BRAIN__")` IS the tick
        # loop's registry, so their brains simply never ran - silently. Latent only
        # because every shipped call passes a single id; `brain_add(role("__player__"),
        # ...)` would have driven exactly one ship.
        agent_parent = parent
        if agent_parent is None:
            agent_parent = get_inventory_value(agent, "__BRAIN__", None)
            if agent_parent is None:
                seq = root_type == BrainType.Sequence
                agent_parent = Brain(agent, "SEQ root" if seq else "SEL root",
                                     None, client_id, root_type)
                set_inventory_value(agent, "__BRAIN__", agent_parent)
        brain_add_parent(agent_parent, agent, label, data, client_id)


__brains_is_running = False
_brain_slicer = RollingSlicer()

def brains_run_all(tick_task, pass_seconds=None):
    """Run agent brains for the current tick.

    Iterates agents with a ``__BRAIN__`` inventory entry and calls
    ``brain.run()``. Re-entrant calls are suppressed with a guard flag; agents
    whose ``Agent.get`` returns ``None`` (or that are paused) are skipped.

    ``pass_seconds`` controls batching:

    * ``None`` (default) - run **all** brains this call (original behavior; kept
      for existing callers/tests).
    * a number - run only a **rolling slice** this call, sized so a full pass
      over every brain completes in about ``pass_seconds`` of sim time. This
      spreads a large fleet's brains across ticks instead of one batch, so no
      single tick spikes. Each brain still runs about once per ``pass_seconds``,
      preserving the prior cadence and total cost.

    Args:
        tick_task: The tick task or event that triggered this run.
        pass_seconds: If set, spread a full pass over ~this many seconds.
    """
    global __brains_is_running
    if __brains_is_running:
        return
    __brains_is_running = True
    try:
        _brains_run_all(tick_task, pass_seconds)
    finally:
        # ALWAYS release the re-entrancy guard. Anything that escapes the body
        # (has_inventory, the slicer, brain_clear) used to leave this stuck True,
        # and then brains_run_all returned immediately FOREVER: every NPC in the
        # game stops thinking, permanently, with no error after the first one.
        # The engine forks a fresh process per mission so it self-heals on the next
        # restart; the dev runner reuses the interpreter, so there it is terminal
        # and reads as "enemies stopped moving after a while / on a later run".
        __brains_is_running = False


def brains_reset() -> None:
    """Drop cross-mission brain scheduler state (called by reset_mission_state)."""
    global __brains_is_running
    __brains_is_running = False
    _brain_slicer.reset()


def brains_is_stalled() -> bool:
    """True if the re-entrancy guard is stuck on (no brain will ever run again).

    Registered with the reset ledger so a restart soak reports it instead of
    leaving a silently AI-less mission.
    """
    return bool(__brains_is_running)


def _brains_run_all(tick_task, pass_seconds=None):
    ids = has_inventory("__BRAIN__")
    # pass_seconds None -> run all (original); else a rolling per-tick slice.
    seq = ids if pass_seconds is None else _brain_slicer.slice(ids, pass_seconds)

    # Brains whose engine object is gone are unscheduled AFTER the loop, never
    # during it: brain_clear mutates the live has_inventory("__BRAIN__") set, and
    # clearing mid-iteration raises "Set changed size during iteration". Stays None
    # (no allocation) on the common path where nothing needs clearing.
    to_unschedule = None

    for agent in seq:
        try:
            # Paused brains are skipped (e.g. while parked on the standby
            # list, so they don't act on a non-simulated object).
            if get_inventory_value(agent, "__BRAIN_PAUSED__", False):
                continue
            agent_root = get_inventory_value(agent, "__BRAIN__")
            # Verify the agent is valid
            agent_obj = Agent.get(agent)
            if agent_obj is None:
                continue
            # __BRAIN__ can resolve to None even though this id is still listed in the
            # class-level has_inventory("__BRAIN__") registry: the brain-carrying object
            # was deleted (leaving a stale registry entry) and its id was then recycled to
            # a NEW object whose own inventory has no brain. Agent.get() returns that new
            # object (non-None), but the per-object __BRAIN__ read is None - so guard it
            # rather than crash on None.run() (previously surfaced as the caught
            # "Exception in brain processing 'NoneType' object has no attribute 'run'").
            if agent_root is None:
                continue
            # Engine-validity guard: never run a brain whose underlying engine object
            # is gone - it would hand a freed id to the C++ layer and trip the engine's
            # VALID_SPACE_OBJ assertion (the mock silently tolerates a dangling id, so
            # this only bites in a real session). A GRID-object brain also dies with its
            # HOST ship: all its grid access goes through get_hull_map(host_id), so a
            # freed host asserts. In either case UNSCHEDULE the brain (brain_clear) so it
            # stops for good, then skip. A host on the standby list still EXISTS
            # (object_exists True) and its brain is paused via __BRAIN_PAUSED__ above, so
            # this never unschedules a merely-parked object.
            if is_grid_object_id(agent):
                host = getattr(agent_obj, "host_id", None)
                if host is None or not object_exists(host):
                    if to_unschedule is None:
                        to_unschedule = []
                    to_unschedule.append(agent)
                    continue
            elif is_space_object_id(agent) and not object_exists(agent):
                if to_unschedule is None:
                    to_unschedule = []
                to_unschedule.append(agent)
                continue
            agent_root.run()
        except Exception as e:
            print(f"Exception in brain processing {e}")
    # Unschedule stale brains now the iteration is done (safe to mutate the set).
    if to_unschedule:
        brain_clear(to_unschedule)
    

