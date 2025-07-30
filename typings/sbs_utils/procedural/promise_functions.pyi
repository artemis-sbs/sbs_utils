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
        (float,float,float) : x, y, path_length"""
def has_role (so, role):
    """check if an agent has a role
    
    Args:
        so (an agent): an agent id or object
        role (str): the role to test for
    
    Returns:
        bool: if the agent has that role"""
def to_data_set (id_or_obj):
    """gets the engine dataset of the specified agent
    
    !!! Note
        Same as to_data_set
    
    Args:
        id_or_obj (agent): Agent id or object
    
    Returns:
        data set| None: Returns the data or None if it does not exist"""
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
class TestPromise(Promise):
    """class TestPromise"""
    def __init__ (self, test_func) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
