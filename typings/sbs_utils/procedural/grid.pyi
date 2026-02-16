from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.helpers import FrameContext
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def add_role (set_holder, role):
    """Add a role to an agent or a set of agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def get_artemis_data_dir_filename (filename):
    """Get the full path to a file in the data directory.
    
    Args:
        filename (str): The relative path from the data directory.
    
    Returns:
        str: The full path to the file in the data directory."""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
def get_open_grid_points (id_or_obj) -> set[sbs_utils.vec.Vec3]:
    """Gets a list of open grid locations
    
    Args:
        id_or_obj (agent): agent id or object to check
    
    Returns:
        set: a set of Vec3 with x and y set"""
def grid_clear_detailed_status (id_or_obj):
    """clears the detailed status string of a grid object
    
    Args:
        id_or_obj (Agent | int): The agent id of object"""
def grid_clear_speech_bubble (id_or_obj):
    """Clear the speech bubble for a grid object
    
    Args:
        id_or_obj (Agent | int): agent id or object of the grid object"""
def grid_clear_target (grid_obj_or_set):
    """Clear the target of a grid object
    
    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): the id of the object or set"""
def grid_close_list (grid_obj, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        the_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        list[CloseData]: The gird close data of the closest objects"""
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_delete_objects (ship_id_or_obj):
    """Delete all grid objects for the given ship.
    Args:
        ship_id_or_obj (Agent | int): The agent or id of the ship."""
def grid_detailed_status (id_or_obj, status, color=None):
    """sets the detailed status of a grid object
    
    Args:
        id_or_obj (Agent | int): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value"""
def grid_get_grid_current_theme ():
    """Get the current grid theme.
    Returns:
        dict: The grid theme dictionary
        * key (str): The key of the theme data, e.g. `name`, `colors`, `icons`, etc.
        * value (any): The value of the theme data."""
def grid_get_grid_data () -> dict:
    """Get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid data objects.
        * key (str): The key of the dict, which is a ship key as defined in shipData.
        * value (dict): A dict with `grid_objects` as a key, and a list of grid object data as the value."""
def grid_get_grid_named_theme (name):
    """Get the grid theme data by name.
    Args:
        name (str): The name of hte grid theme data.
    Returns:
        dict: The grid theme dictionary
        * key (str): The key of the theme data, e.g. `name`, `colors`, `icons`, etc.
        * value (any): The value of the theme data."""
def grid_get_grid_theme ():
    """Get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid theme data
        * key (str): The ship key associated with the grid theme
        * value (dict): The grid theme data"""
def grid_get_item_theme_data (roles, name=None):
    """Get the item theme data for grid objects with the specified roles, for the optionally specified theme.
    Args:
        roles (str): A comma-separated list of roles to use.
        name (str, optional): The name of the grid data theme. Default is None.
    Returns:
        RetVal: An object containing the `icon`, `scale`, `color`, and `damage_color` for the grid objects that match the roles."""
def grid_objects (so_id) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship
    
    Args:
        so_id (Agent | int): agent id or object
    
    Returns:
        set[int]: a set of agent ids"""
def grid_objects_at (so_id, x, y) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship, at the location specified
    
    Args:
        so_id (Agent | int): agent id or object
        x (int): The x grid location
        y (int): The y grid location
    
    Returns:
        set[int]: A set of agent ids"""
def grid_pos_data (id):
    """get a set of agent ids of the grid objects on the specified ship, at the location specified
    
    Args:
        so_id (agent): agent id or object
        x (int): The x grid location
        y (int): The y grid location
    
    Returns:
        tuple (float,float,float): x, y, path_length"""
def grid_remove_move_role (event):
    """Remove the `_moving_` role from the grid object if the event has the `finished_path` sub_tag.
    Args:
        event (event): The event that caused the removal"""
def grid_set_grid_current_theme (i):
    """Set the grid theme by index.
    Args:
        i (int): The index of the grid theme to use. """
def grid_set_grid_named_theme (name):
    """Set the grid theme by name.
    Args:
        name (str): The name of the grid theme, e.g. `cosmos` or `Retro`."""
def grid_short_status (id_or_obj, status, color=None, seconds=0, minutes=0):
    """sets the short status (tool tip) and speech bubble text of a grid object
    
    Args:
        id_or_obj (Agent | int): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble"""
def grid_speech_bubble (id_or_obj, status, color=None, seconds=0, minutes=0):
    """Sets the speech bubble text of a grid object. The text will disappear if the seconds/minutes are set
    
    Args:
        id_or_obj (Agent | int): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble"""
def grid_target (grid_obj_or_set, target_id: int, speed=0.01):
    """Set a grid object to target the location of another grid object
    
    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): an id, object or set of agent(s)
        target_id (Agent): an agent id or object
        speed (float, optional): the speed to move. Defaults to 0.01."""
def grid_target_closest (grid_obj_or_set, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): The agent or set
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        GridCloseData: The gird close data of the closest object"""
def grid_target_pos (grid_obj_or_set, x: float, y: float, speed=0.01):
    """Set the grid object go to the target location
    
    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): An id, object or set of grid object agent(s)
        x (float): x location
        y (float): y location
        speed (float, optional): The grid object speed. Defaults to 0.01."""
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def remove_role (agents, role):
    """Remove a role from an agent or a set of agents.a
    
    Args:
        agents (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def to_blob (id_or_obj):
    """Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_data_set
    Args:
        id_or_obj (Agent | int): Agent id or object
    Returns:
        data_set | None: Returns the data or None if it does not exist"""
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
def to_object_list (the_set):
    """Converts a set to a list of objects
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[Agent]: A list of Agent objects"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a set of ids
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        set[Agent | CloseData | int]: A set containing whatever was passed in."""
