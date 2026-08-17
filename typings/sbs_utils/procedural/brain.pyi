from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from enum import IntFlag
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import RollingSlicer
from sbs_utils.tickdispatcher import TickDispatcher
def _brains_run_all (tick_task, pass_seconds=None):
    ...
def brain_add (agent_id_or_set, label, data=None, client_id=0, parent=None):
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
            None (attaches to the agent's root Select node).
    
    Example:
        brain_add(ENEMY_ID, patrol_label)
        brain_add(ENEMY_ID, {"SEL_combat": [attack_label, evade_label]})"""
def brain_add_parent (parent, agent, label, data=None, client_id=0):
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
            Defaults to 0 (server)."""
def brain_clear (agent_id_or_set):
    """Remove the behaviour-tree brain from one or more agents.
    
    Clears the ``__BRAIN__`` inventory key so the agent's brain stops running
    on the next tick. Does not explicitly stop any sub-tasks already started
    by brain labels.
    
    Args:
        agent_id_or_set: Agent ID, object, or set/list of either.
    
    Example:
        brain_clear(ENEMY_ID)"""
def brain_pause (agent_id_or_set, paused=True):
    """Pause (or resume) one or more agents' brains without removing them.
    
    A paused brain is skipped by ``brains_run_all`` until resumed - used when an
    object is parked on the standby list so its brain doesn't act on a
    non-simulated object. The brain tree is preserved (unlike ``brain_clear``).
    
    Args:
        agent_id_or_set: Agent ID, object, or set/list of either.
        paused (bool, optional): True to pause, False to resume. Defaults True."""
def brain_resume (agent_id_or_set):
    """Resume one or more agents' brains (see ``brain_pause``)."""
def brain_schedule ():
    """Schedule the brain tick task via the objective system."""
def brains_is_stalled () -> bool:
    """True if the re-entrancy guard is stuck on (no brain will ever run again).
    
    Registered with the reset ledger so a restart soak reports it instead of
    leaving a silently AI-less mission."""
def brains_reset () -> None:
    """Drop cross-mission brain scheduler state (called by reset_mission_state)."""
def brains_run_all (tick_task, pass_seconds=None):
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
        pass_seconds: If set, spread a full pass over ~this many seconds."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def has_inventory (key: str):
    """Return the set of agent IDs that have an inventory entry for the given key.
    
    Args:
        key (str): The inventory key to look for.
    
    Returns:
        set[int]: IDs of all agents that have this key set."""
def is_grid_object_id (id):
    """Return whether an ID belongs to an engineering-grid object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the grid-object bit (0x2000…) is set."""
def is_space_object_id (id):
    """Return whether an ID belongs to a space object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the space-object bit (0x4000…) is set."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
class Brain(object):
    """class Brain"""
    def __init__ (self, agent, label, data, client_id, brain_type=<BrainType.Simple: 256>):
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def active (self):
        ...
    @property
    def active_desc (self):
        ...
    def add_child (self, child):
        ...
    @property
    def result (self):
        ...
    @result.setter
    def result (self, res):
        ...
    def run (self):
        ...
    def run_select (self):
        ...
    def run_sequence (self):
        ...
    def run_simple (self):
        ...
    def run_sub_label (self, loc):
        ...
class BrainType(IntFlag):
    """Support for integer-based Flags"""
    AlwayFail : 4
    AlwaySuccess : 8
    Invert : 2
    Select : 1024
    Sequence : 512
    Simple : 256
