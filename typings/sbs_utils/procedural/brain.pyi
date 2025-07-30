from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from enum import IntFlag
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.pollresults import PollResults
def brain_add (agent_id_or_set, label, data=None, client_id=0, parent=None):
    ...
def brain_add_parent (parent, agent, label, data=None, client_id=0):
    ...
def brain_clear (agent_id_or_set):
    ...
def brain_schedule ():
    ...
def brains_run_all (tick_task):
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def has_inventory (key: str):
    """get the set of agent ids that have a inventory item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set: set of ids"""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a set of ids
    
    Args:
        the_set (set): set, list or single item
    
    Returns:
        set of things"""
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
