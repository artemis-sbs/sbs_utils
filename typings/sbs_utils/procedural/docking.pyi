from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.tickdispatcher import TickTask
def _docking_handle_dock_start (player, npc, brain):
    ...
def _docking_handle_docked (player, npc, brain):
    ...
def _docking_handle_docking (player, npc, brain):
    ...
def _docking_handle_undocked (player_id, player, pairs):
    ...
def _docking_handle_undocking (player, npc, brain):
    ...
def _docking_run_task (player, npc, brain, inner_label):
    ...
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """get the  close data that matches the test set, max_dist and optional filter function
    
    Args:
        the_ship (agent): The agent ID or object
        the_set (agent set): The set of objects to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (func, optional): An additional function to test with. Defaults to None.
    
    Returns:
        CloseData: The close object close data to get the distance"""
def docking_run_all (tick_task):
    ...
def docking_schedule ():
    ...
def docking_set_docking_logic (player_set, npc_set, label, data=None):
    ...
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def signal_emit (name, data=None):
    ...
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
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
class _DockingBrain(object):
    """class _DockingBrain"""
    def __init__ (self, label, data):
        """Initialize self.  See help(type(self)) for accurate signature."""
