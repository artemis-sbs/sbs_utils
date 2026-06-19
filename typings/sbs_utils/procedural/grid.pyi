from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.helpers import FrameContext
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def get_artemis_data_dir_filename (filename):
    """Get the full path to a file in the data directory.
    
    Args:
        filename (str): The relative path from the data directory.
    
    Returns:
        str: The full path to the file in the data directory."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
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
    """Clear the detailed status (info text) of a grid object.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object."""
def grid_clear_speech_bubble (id_or_obj):
    """Clear the speech bubble for a grid object
    
    Args:
        id_or_obj (Agent | int): agent id or object of the grid object"""
def grid_clear_target (grid_obj_or_set):
    """Clear the movement target of a grid object, stopping it in place.
    
    Args:
        grid_obj_or_set (Agent | int | set): Agent, ID, or set of grid
            object(s) to stop."""
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
    """Delete all grid objects belonging to a ship.
    
    Args:
        ship_id_or_obj (Agent | int): Agent or ID of the ship whose grid
            objects should be removed."""
def grid_detailed_status (id_or_obj, status, color=None):
    """Set the detailed status (info text) of a grid object.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        status (str): Status string to display.
        color (str, optional): Text color. ``None`` keeps the current value.
            Defaults to None."""
def grid_get_grid_current_theme ():
    """Get the currently active grid theme data.
    
    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc."""
def grid_get_grid_data () -> dict:
    """Get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid data objects.
        * key (str): The key of the dict, which is a ship key as defined in shipData.
        * value (dict): A dict with `grid_objects` as a key, and a list of grid object data as the value."""
def grid_get_grid_named_theme (name):
    """Get a grid theme by name, falling back to the current theme if not found.
    
    Args:
        name (str | None): Theme name to look up (case-insensitive), or
            ``None`` to return the current theme.
    
    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc."""
def grid_get_grid_theme ():
    """Get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid theme data
        * key (str): The ship key associated with the grid theme
        * value (dict): The grid theme data"""
def grid_get_item_theme_data (roles, name=None):
    """Get icon, scale, color, and damage color for a set of roles from the grid theme.
    
    Roles are matched in reverse priority order so the last role in the list
    takes precedence. Falls back to ``"default"`` entries when no role matches.
    
    Args:
        roles (str): Comma-separated role names.
        name (str | None, optional): Theme name to use. ``None`` uses the
            current theme. Defaults to None.
    
    Returns:
        RetVal: Object with ``.icon`` (int), ``.scale`` (float), ``.color``
            (str), and ``.damage_color`` (str) attributes."""
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
    """Return the current position and path length of a grid object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        tuple[float, float, float]: ``(curx, cury, path_length)``."""
def grid_remove_move_role (event):
    """Remove the ``_moving_`` role when a grid object finishes its path.
    
    Args:
        event: Engine event; only acts when ``event.sub_tag == "finished_path"``."""
def grid_set_grid_current_theme (i):
    """Set the active grid theme by index.
    
    Args:
        i (int): Index into the loaded grid theme list."""
def grid_set_grid_named_theme (name):
    """Set the active grid theme by name.
    
    Args:
        name (str): Theme name (case-insensitive), e.g. ``"cosmos"`` or
            ``"Retro"``."""
def grid_short_status (id_or_obj, status, color=None, seconds=0, minutes=0):
    """Set the tooltip and speech bubble text of a grid object.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        status (str): Status string for both the tooltip and speech bubble.
        color (str, optional): Text color. ``None`` keeps the current value.
            Defaults to None.
        seconds (int, optional): Duration for the speech bubble. Defaults to 0
            (permanent).
        minutes (int, optional): Additional minutes for the bubble duration.
            Defaults to 0."""
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
    """Set a grid object to move toward a specific grid coordinate.
    
    Args:
        grid_obj_or_set (Agent | int | set): Agent, ID, or set of grid
            object(s) to move.
        x (float): Target x grid coordinate.
        y (float): Target y grid coordinate.
        speed (float, optional): Movement speed. Defaults to 0.01."""
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
