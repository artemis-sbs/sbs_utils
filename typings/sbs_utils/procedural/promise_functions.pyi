from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.vec import Vec3
def awaitable (func):
    ...
def destroyed_all (*args, **kwargs):
    ...
def destroyed_any (*args, **kwargs):
    ...
def distance_greater (*args, **kwargs):
    ...
def distance_less (*args, **kwargs):
    ...
def distance_point_greater (*args, **kwargs):
    ...
def distance_point_less (*args, **kwargs):
    ...
def grid_arrive_id (*args, **kwargs):
    ...
def grid_arrive_location (*args, **kwargs):
    ...
def grid_pos_data (id):
    """get a set of agent ids of the grid objects on the specified ship, at the location specified
    
    Args:
        so_id (agent): agent id or object
        x (int): The x grid location
        y (int): The y grid location
    
    Returns:
        tuple (float,float,float): x, y, path_length"""
def has_role (so, role):
    """Check if an agent has the specified role.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): The role to test for
    
    Returns:
        bool: True if the agent has that role"""
def to_data_set (id_or_obj):
    """Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_blob
    Args:
        id_or_obj (Agent | int): Agent id or object
    Returns:
        data_set | None: Returns the data or None if it does not exist"""
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
class TestPromise(Promise):
    """class TestPromise"""
    def __init__ (self, test_func) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
