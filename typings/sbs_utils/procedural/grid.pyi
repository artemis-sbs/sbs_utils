from sbs_utils.agent import CloseData
from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def get_artemis_data_dir_filename (filename):
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def get_mission_dir_filename (filename):
    ...
def get_open_grid_points (id_or_obj):
    """gets a list of open grid location
    
    Args:
        id_or_obj (agent): agent id or object to check
    
    Returns:
        set: a set of Vec3 with x and y set"""
def grid_clear_detailed_status (id_or_obj):
    """clears the detailed status string of a grid object
    
    Args:
        id_or_obj (agent): The agent id of object"""
def grid_clear_speech_bubble (id_or_obj):
    """clear the speech bubble for a grid object
    
    Args:
        id_or_obj (agent): agent id or object of the grid object"""
def grid_clear_target (grid_obj_or_set):
    """Clear the target of a grid object
    
    Args:
        grid_obj_or_set (agent): the id of the object or set"""
def grid_close_list (grid_obj, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj_or_set (agent set): The agent
        target_set (agent set, optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (_type_, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData list: The gird close data of the closest objects"""
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj_or_set (agent set): The agent
        target_set (agent set, optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (_type_, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_detailed_status (id_or_obj, status, color=None):
    """sets the detailed status of a grid object
    
    Args:
        id_or_obj (agent): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value"""
def grid_get_grid_current_theme ():
    ...
def grid_get_grid_data ():
    """get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid data objects key is a ship key"""
def grid_get_grid_named_theme (name):
    ...
def grid_get_grid_theme ():
    """get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid data objects key is a ship key"""
def grid_get_item_theme_data (roles, name=None):
    ...
def grid_objects (so_id):
    """get a set of agent ids of the grid objects on the specified ship
    
    Args:
        so_id (agent): agent id or object
    
    Returns:
        set: a set of agent ids"""
def grid_objects_at (so_id, x, y):
    """get a set of agent ids of the grid objects on the specified ship, at the location specified
    
    Args:
        so_id (agent): agent id or object
        x (int): The x grid location
        y (int): The y grid location
    
    Returns:
        set: a set of agent ids"""
def grid_set_grid_current_theme (i):
    ...
def grid_set_grid_named_theme (name):
    ...
def grid_short_status (id_or_obj, status, color=None, seconds=0, minutes=0):
    """sets the short status (tool tip) and speech bubble text of a grid object
    
    Args:
        id_or_obj (agent): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble"""
def grid_speech_bubble (id_or_obj, status, color=None, seconds=0, minutes=0):
    """sets the speech bubble text of a grid object. The text will disappear if the seconds/minutes are set
    
    Args:
        id_or_obj (agent): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble"""
def grid_target (grid_obj_or_set, target_id: int, speed=0.01):
    """Set a grid object to target the location of another grid object
    
    Args:
        grid_obj_or_set (agent): an id, object or set of agent(s)
        target_id (agent): an agent id or object
        speed (float, optional): the speed to move. Defaults to 0.01."""
def grid_target_closest (grid_obj_or_set, target_set=None, max_dist=None, filter_func=None):
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj_or_set (agent set): The agent
        target_set (agent set, optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (_type_, optional): additional filer function. Defaults to None.
    
    Returns:
        GridCloseData: The gird close data of the closest object"""
def grid_target_pos (grid_obj_or_set, x: float, y: float, speed=0.01):
    """Set the grid object go to the target location
    
    Args:
        grid_obj_or_set (agent): An id, object or set of grid object agent(s)
        x (float): x location
        y (float): y location
        speed (float, optional): The grid object speed. Defaults to 0.01."""
def load_json_data (file):
    ...
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def to_blob (id_or_obj):
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
def to_object_list (the_set):
    """to_object_list
    converts a set to a list of objects
    
    Args:
        the_set (set|list): a set of agent ids
    
    Returns:
        list: of Agents"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a set of ids
    
    Args:
        the_set (set): set, list or single item
    
    Returns:
        set of things"""
