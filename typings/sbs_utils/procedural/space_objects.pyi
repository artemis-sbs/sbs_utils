from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
def all_roles (roles: str):
    """Returns a set of all the agents which have all of the given roles.
    
    Args:
        roles (str): A comma-separated list of roles.
    
    Returns:
        set[int]: a set of agent IDs."""
def broad_test (x1: float, z1: float, x2: float, z2: float, broad_type=65520):
    """Returns a set of ids that are in the target rect.
    Args:
        x1 (float): x location (left)
        z1 (float): z location (top)
        x2 (float): x location (right)
        z2 (float): z location (bottom)
        broad_type (int, optional): The type of objects for which to search.
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0xfff0
    Returns:
        set[int]: A set of ids"""
def broad_test_around (id_or_obj, width: float, depth: float, broad_type=65520):
    """Returns a set of ids that are around the specified object in the target rect.
    Args:
        id_obj (Agent | int): The ID or object of an agent
        w (float): width
        d (float): depth
        broad_type (int, optional): The type of objects for which to search.
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0xfff0
    Returns:
        set[int]: A set of ids"""
def clear_target (chasers: set | int | sbs_utils.agent.Agent | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, throttle=0):
    """Clear the target on an agent or set of agents.
    
    Args:
        chasers (set[Agent | int] | int | Agent | CloseData | SpawnData): an agent or set of agents"""
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Get the CloseData that matches the test set, max_dist, and optional filter function.
    
    Args:
        the_ship (Agent | int): The agent ID or object
        the_set (Agent | int | set[Agent | int]): The agent or id or set of objects or ids to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (Callable, optional): An additional function to test with. Defaults to None.
    
    Returns:
        CloseData: The closest object's CloseData to get the distance."""
def closest_list (source: int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData | sbs_utils.agent.Agent, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """Get the list of close data that matches the test set, max_dist, and optional filter function.
    Args:
        source (Agent | int | CloseData | SpawnData): The agent object or id of the agent.
        the_set (set[int]): A set of ids to check against.
        max_dist (float, optional): The maximum distance to include. Defaults to None.
        filter_func (Callable, optional): An additional function to check against. Defaults to None.
    
    Returns:
        list[CloseData]: The list of CloseData representing the close objects to get the distance."""
def closest_object (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.Agent:
    """Get the CloseData that matches the test set, max_dist, and optional filter function.
    
    Args:
        the_ship (Agent | int): The agent ID or object.
        the_set (Agent | int | set[Agent | int]): The id or object or set of objects or ids to test against.
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (func, optional): An additional function to test with. Defaults to None.
    
    Returns:
        agent: Return the closest agents or None"""
def delete_object (id_or_objs):
    """Delete the specified object or set of objects.
    Args:
        id_or_objs (Agent | int | set[Agent | int]): The object or set of objects."""
def delete_objects_box (x, y, z, w, h, d, broad_type=15, roles=None):
    """Removes items from an area
    
    Args:
        x,y,z (float,float,float): the start point/origin
        radius (float): the radius
        broad_type (int, optional): The engine level bit test for broadtest
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0x0F
        roles (str, optional): A comma-separated list of roles that the objects must have to be deleted."""
def delete_objects_sphere (x, y, z, radius, broad_type=15, roles=None):
    """Removes items from an area if they meet the broadtype and role filter requirements.
    
    Args:
        x,y,z (float,float,float): The start point/origin of the sphere.
        radius (float): The radius of the sphere.
        broad_type (int, optional) The engine level bit test for broadtest.
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0x0F
        roles (str, optional): A comma-separated list of roles that the objects must have to be deleted."""
def get_engineering_value (id_or_obj, name, default=None):
    """Gets an engineering value by name.
    
    Args:
        id_or_obj (Agent | int): An agent id or object.
        name (str): The engineering value to get.
        default (float, optional): What to return if not found. Defaults to None.
    
    Returns:
        float: A value or the default"""
def get_pos (id_or_obj):
    """Get the position of an agent.
    
    Args:
        id_or_obj (Agent | int): The agent for which to get the position.
    
    Returns:
        Vec3 | None: The position of the agent or None if it doesn't exist."""
def object_exists (so_id):
    """Check the engine to see if the item exists
    Args:
        so_id (Agent | int): agent like data converted to id internally
    Returns:
        bool: if the object exists in the engine"""
def set_engineering_value (id_or_obj, name, value):
    """Sets an engineering value by name
    
    Args:
        id_or_obj (Agent | int): An agent id or object.
        name (str): The engineering value to set.
        value (float): The value."""
def set_pos (id_or_obj, x, y=None, z=None):
    """Set the position of an agent or set of agents.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): An agent or set of agent IDs or objects.
        x (float | Vec3): The x location or a vector.
        y (float, optional): y location. If None, `x` is assumed to be a Vec3. Defaults to None.
        z (float, optional): z location. Defaults to None."""
def target (set_or_object, target_id, shoot: bool = True, throttle: float = 1.0, stop_dist=None):
    """Set the target for an agent or set of agents.
    Args:
        set_or_object (Agent | int | set[Agent | int]): The agent or set of agents for which to set the target.
        target_id (Agent | int): The agent id or object to target.
        shoot (bool, optional): Whether to also lock weapons on target. Defaults to True.
        throttle (float, optional): The speed at which to travel. Defaults to 1.0.
        stop_dist (int, optional): If the target is within this distance, then the throttle will be set to 0. Default is None."""
def target_pos (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, x: float, y: float, z: float, throttle: float = 1.0, target_id=None, stop_dist=None):
    """Set the target position of an agent or set of agents
    
    Args:
        chasers (Agent | int | set[Agent | int]): The agents which should go to the target position.
        x (float): x location
        y (float): y location
        z (float): z location
        throttle (float, optional): The speed at which to travel. Defaults to 1.0.
        target_id (id, optional): What to shoot
        stop_dist (float, optional): If the target position is within this distance, then the throttle will be set to 0. Default is None."""
def target_shoot (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, target_id=None):
    """Set the target id only
    Args:
        chasers (agent id | agent set): the agents to set
        target_id (id, optional): What to shoot"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a list
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        list[Agent | CloseData | int]: A list containing whatever was passed in."""
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
