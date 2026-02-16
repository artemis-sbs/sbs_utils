from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.vec import Vec3
def awaitable (func):
    ...
def destroyed_all (the_set, snapshot=False):
    """Build a Promise that waits until all objects in the set are destroyed.
    Args:
        the_set (set[id])
        snapshot (bool, optional): If True, the set checked will not change if the original set changes.
    Returns:
        TestPromise: The promise."""
def destroyed_any (the_set, snapshot=False):
    """Build a Promise that waits until any objects in the set are destroyed.
    Args:
        the_set (set[id])
        snapshot (bool, optional): If True, the set checked will not change if the original set changes.
    Returns:
        TestPromise: The promise."""
def distance_greater (obj_or_id1, obj_or_id2, distance):
    """Build a Promise that waits until the distance between the two objects is greater than the specified value.
    Args:
        id1 (Agent | int): The agent or ID of the first space object.
        id2 (Agent | int): The agent or ID of the second space object.
        distance (int): The distance between the two objects.
    Returns:
        Promise: The promise"""
def distance_less (obj_or_id1, obj_or_id2, distance):
    """Build a Promise that waits until the distance between the two objects is less than the specified value.
    Args:
        id1 (Agent | int): The agent or ID of the first space object.
        id2 (Agent | int): The agent or ID of the second space object.
        distance (int): The distance between the two objects.
    Returns:
        Promise: The promise"""
def distance_point_greater (obj_or_id, point, distance):
    """Build a Promise that waits until the distance between the object and the point is less than the specified value.
    Args:
        obj_or_id (Agent | int): The agent or ID of the space object.
        point (Vec3): The point.
        distance (int): The distance between the object and the point.
    Returns:
        Promise: The promise"""
def distance_point_less (obj_or_id, point, distance):
    """Build a Promise that waits until the distance between the object and the point is less than the specified value.
    Args:
        obj_or_id (int): The agent or ID of the space object.
        point (Vec3): The point.
        distance (int): The distance between the object and the point.
    Returns:
        Promise: The promise"""
def grid_arrive_id (the_set, target_id, snapshot=False):
    """Build a Promise that waits until the grid object agents have completed their movement.
    Args:
        the_set (Agent | int | set[Agent | int]): The grid object or id or set to check
        target_id (int): The target grid object ID
        snapshot (bool, optional): If True, the set checked will not change if the original set changes."""
def grid_arrive_location (the_set, x=0, y=0, snapshot=False):
    """Build a Promise that waits until the grid object agents have completed their movement.
    Args:
        the_set (Agent | int | set[Agent | int]): The grid object or id or set to check
        x (int, optional): Not used
        y (int, optional): Not used
        snapshot (bool, optional): If True, the set checked will not change if the original set changes.
    Returns:
        TestPromise: The promise."""
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
