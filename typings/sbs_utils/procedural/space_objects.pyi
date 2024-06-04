from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
def broad_test (x1: float, z1: float, x2: float, z2: float, broad_type=65520):
    """returns a set of ids that are in the target rect
    
    Args:
        x1(float): x location (left)
        z1(float): z location (top)
        x2(float): x location (right)
        z2(float): z location (bottom)
        broad_type (int, optional): -1=All, 0=player, 1=Active, 2=Passive. Defaults to -1.
    
    Returns:
        set: A set of ids"""
def broad_test_around (id_or_obj, width: float, depth: float, broad_type=65520):
    """returns a set of ids that are around the specified object in the target rect
    
    Args:
        id_obj(agent): The ID or object of an agent
        w(float): width
        d(float): depth
        broad_type (int, optional): -1=All, 0=player, 1=Active, 2=Passive. Defaults to -1.
    
    Returns:
        set: A set of ids"""
def clear_target (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData):
    """clear the target on an agent or set of agents
    
    Args:
        chasers (set | int | CloseData | SpawnData): an agent or set of agents"""
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """get the  close data that matches the test set, max_dist and optional filter function
    
    Args:
        the_ship (agent): The agent ID or object
        the_set (agent set): The set of objects to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (func, optional): An additional function to test with. Defaults to None.
    
    Returns:
        CloseData: The close object close data to get the distance"""
def closest_list (source: int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData | sbs_utils.agent.Agent, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """get the list of close data that matches the test set, max_dist and optional filter function
    
    Args:
        source (agent): The agent object or id of the agent
        the_set (agents set): a set of ids to check against
        max_dist (float, optional): The maximum distance to include. Defaults to None.
        filter_func (function, optional): an additional function to check against. Defaults to None.
    
    Returns:
        list[CloseData]: The list of close objects With close data to get the distance"""
def closest_object (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.Agent:
    """get the  close data that matches the test set, max_dist and optional filter function
    
    Args:
        the_ship (agent): The agent ID or object
        the_set (agent set): The set of objects to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (func, optional): An additional function to test with. Defaults to None.
    
    Returns:
        agent: Return the closest agents or None"""
def get_engineering_value (id_or_obj, name, default=None):
    """gets an engineering value by name
    
    Args:
        id_or_obj (agent): An agent id or object
        name (str): The value to get
        default (float, optional): What to return if not found. Defaults to None.
    
    Returns:
        float: A value or the default"""
def get_pos (id_or_obj):
    """get the position of an agent
    
    Args:
        id_or_obj (agent id | agent): The agent to set position on
    
    Returns:
        Vec3: _description_"""
def object_exists (so_id):
    """check the engine to see if the item exists
    
    Args:
        so_id (agent): agent like data converted to id internally
    
    Returns:
        bool: if the object exists in the engine"""
def set_engineering_value (id_or_obj, name, value):
    """sets an engineering value by name
    
    Args:
        id_or_obj (agent): An agent id or object
        name (str): The value to get
        value (float): The value"""
def set_pos (id_or_obj, x, y=None, z=None):
    """set the position of an agent or set of agents
    
    Args:
        id_or_obj (agent|set of agent): an agent or set of agent IDs or objects
        x (float| Cec3): The x location or a vector
        y (float, optional): y location. Defaults to None.
        z (float, optional):z location. Defaults to None."""
def target (set_or_object, target_id, shoot: bool = True, throttle: float = 1.0, stop_dist=None):
    """set Target a target for an agent/set of agents
    
    Args:
        set_or_object (agent, set): the agent or set of object to set the target on
        target_id (agent): agent id or object to target
        shoot (bool, optional): whether to also lock weapons on target. Defaults to True.
        throttle (float, optional): The speed to travel at. Defaults to 1.0."""
def target_pos (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, x: float, y: float, z: float, throttle: float = 1.0, target_id=None, stop_dist=None):
    """Set the target position of an agent or set of agents
    
    Args:
        chasers (agent id | agent set): the agents to set
        x (float): x location
        y (float): y location
        z (float): z location
        throttle (float, optional): The speed to go. Defaults to 1.0.
        target_id (id, optional): What to shoot
        stop_dist (float, optional): The distance to stop"""
def target_shoot (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, target_id=None):
    """Set the target id only
    Args:
        chasers (agent id | agent set): the agents to set
        target_id (id, optional): What to shoot"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a list
    
    Args:
        the_set (set|list): a set of agent ids
    
    Returns:
        list: containing whatever was passed in"""
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
