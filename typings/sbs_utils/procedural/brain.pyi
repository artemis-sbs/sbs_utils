from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from enum import IntFlag
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.pollresults import PollResults
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
def brain_schedule ():
    """Schedule the brain tick task via the objective system."""
def brains_run_all (tick_task):
    """Run all agent brains for the current tick.
    
    Iterates every agent with a ``__BRAIN__`` inventory entry and calls
    ``brain.run()``. Re-entrant calls are suppressed with a guard flag.
    Agents whose ``Agent.get`` returns ``None`` are silently skipped.
    
    Args:
        tick_task: The tick task or event that triggered this run."""
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
    """int([x]) -> integer
    int(x, base=10) -> integer
    
    Convert a number or string to an integer, or return 0 if no arguments
    are given.  If x is a number, return x.__int__().  For floating point
    numbers, this truncates towards zero.
    
    If x is not a number or if base is given, then x must be a string,
    bytes, or bytearray instance representing an integer literal in the
    given base.  The literal can be preceded by '+' or '-' and be surrounded
    by whitespace.  The base defaults to 10.  Valid bases are 0 and 2-36.
    Base 0 means to interpret the base from the string as an integer literal.
    >>> int('0b100', base=0)
    4"""
    AlwayFail : 4
    AlwaySuccess : 8
    Invert : 2
    Select : 1024
    Sequence : 512
    Simple : 256
