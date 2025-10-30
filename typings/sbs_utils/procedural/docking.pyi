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
    """Get the CloseData that matches the test set, max_dist, and optional filter function.
    
    Args:
        the_ship (Agent | int): The agent ID or object
        the_set (Agent | int | set[Agent | int]): The agent or id or set of objects or ids to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (Callable, optional): An additional function to test with. Defaults to None.
    
    Returns:
        CloseData: The closest object's CloseData to get the distance."""
def docking_run_all (tick_task):
    ...
def docking_schedule ():
    ...
def docking_set_docking_logic (player_set, npc_set, label, data=None):
    ...
def role (role: str):
    """Returns a set of all the agents with a given role as a set of IDs.
    
    Args:
        role (str): The role.
    
    Returns:
        set[int]: a set of agent IDs."""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def signal_emit (name, data=None):
    """Emit a signal to trigger all instances of the signal route to run.
    Args:
        name (str): The name of the signal.
        data (dict): The data to provide to the signal route."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a set of ids
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        set[Agent | CloseData | int]: A set containing whatever was passed in."""
class _DockingBrain(object):
    """class _DockingBrain"""
    def __init__ (self, label, data):
        """Initialize self.  See help(type(self)) for accurate signature."""
