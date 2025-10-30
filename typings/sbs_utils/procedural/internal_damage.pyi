from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def add_role (set_holder, role):
    """Add a role to an agent or a set of agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def all_roles (roles: str):
    """Returns a set of all the agents which have all of the given roles.
    
    Args:
        roles (str): A comma-separated list of roles.
    
    Returns:
        set[int]: a set of agent IDs."""
def comms_broadcast (ids_or_obj, msg, color=None) -> None:
    """Send text to the text waterfall
    The ids can be player ship ids or client/console ids
    
    Args:
        ids_or_obj (id or objecr): A set or single id or object to send to,
        msg (str): The text to send
        color (str, optional): The Color for the text. Defaults to "#fff"."""
def convert_system_to_string (the_system):
    """Convert the SBS.SHIPSYS enum value or string to a string.
    Args:
        the_system (SYS.SHIPSYSTEM | string): The enum value or string
    Returns:
        str: The string representation of the system, e.g. `weapon`."""
def explode_player_ship (id_or_obj):
    """The specified ship will be destroyed, but not immediately. This will trigger the `player_ship_destroyed` signal, which will allow things to happen prior to the ship being deleted.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship."""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_pos (id_or_obj):
    """Get the position of an agent.
    
    Args:
        id_or_obj (Agent | int): The agent for which to get the position.
    
    Returns:
        Vec3 | None: The position of the agent or None if it doesn't exist."""
def grid_apply_system_damage (id_or_obj):
    """Damage a random system node on the specified ship.
    Args:
        id_or_obj (Agent | int): The agent or id of the specified ship."""
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_count_grid_data (ship_key, role, default=0):
    """Count the amount of grid items with the give role(from the json data)
    for the given ship.
    Args:
        ship_key (str): The ship key to use to find the grid items
        role (str): A comma-separated list of roles for which to check
        default (int, optional): If the data for the grid key specified is not found, this number will be returned. Default is 0."""
def grid_damage_grid_object (ship_id, grid_id, damage_color):
    """Damage the specified grid object associated with the specified ship, and give it a color.
    Args:
        ship_id (Agent | int): The agent or id of the ship
        grid_id (Agent | int): The agent or id of the grid object
        damage_color (str): The color of the damage grid object"""
def grid_damage_hallway (id_or_obj, loc_x, loc_y, damage_color):
    """Damage a grid location that is not already a grid object.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship.
        loc_x (int): The x position of the hallway
        loc_y (int): The y position of the hallway
        damage_color (str): The color that should be applied to the grid object icon."""
def grid_damage_pos (id_or_obj, loc_x, loc_y):
    """Damage the ship's grid at the specified coordinates.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship
        loc_x (int): The x coordinate of the grid position
        loc_y (int): The y coordinate of the grid position"""
def grid_damage_system (id_or_obj, the_system=None):
    """grid_damage_system
    
    Damage a system using the grid objects of the ship
    Args:
        id_or_obj (Agent | int | CloseData | SpawnData): the ship to damage
        the_system (SBS.SHIPSYS | int | str | None, optional): The system to damage, None picks random
    Returns:
        bool: True if the system is damaged, otherwise False"""
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
def grid_get_item_theme_data (roles, name=None):
    """Get the item theme data for grid objects with the specified roles, for the optionally specified theme.
    Args:
        roles (str): A comma-separated list of roles to use.
        name (str, optional): The name of the grid data theme. Default is None.
    Returns:
        RetVal: An object containing the `icon`, `scale`, `color`, and `damage_color` for the grid objects that match the roles."""
def grid_get_max_hp ():
    ...
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
def grid_rebuild_grid_objects (id_or_obj, grid_data=None):
    ...
def grid_repair_grid_objects (player_ship, id_or_set, who_repaired=None):
    """Repair the provided grid objects.
    Note: More details on the use of this function required.
    Args:
        player_ship (Agent | int): The agent or id of the ship
        id_or_set (Agent | int | set[Agent | int]): The grid object or set of grid objects to repair
        who_repaired (Agent | int): The agent (damcon team) that did the work."""
def grid_repair_system_damage (id_or_obj, the_system=None):
    """Repair damage for the specified system. If None, a random node is repaired.
    Args:
        id_or_obj (Agent | int): The agent or id.
        the_system (SBS.SHIPSYS | str | int | None, optional): The system to repair."""
def grid_restore_damcons (id_or_obj):
    """Restore all damcon teams for the specified ship to full health.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship"""
def grid_set_max_hp (max_hp):
    ...
def grid_spawn (id, name, tag, x, y, icon_index, color, roles):
    """Spawn a grid object on a ship.
    
    Args:
        id (Agent | int): The agent to which the grid object should be added
        name (str): The name of the grid object
        tag (str): The tag/side
        x (int): the x grid location
        y (int): the y grid location
        icon_index (int): the icon index
        color (str): color
        roles (str): string of comma-separated roles
    
    Returns:
        GridObject: The grid object."""
def grid_take_internal_damage_at (id_or_obj, source_point, system_hit=None, damage_amount=None):
    """Damage the ship's grid at the specified point in 3D.
    Args:
        id_or_obj (Agent | int): The agent or id
        source_point (Vec3): The point at which damage should be applied.
        system_hit (SBS.SHIPSYS | int | str | None, optional): The system to which damage should be applied. Unused.
        damage_amount (int | None, optional): The damage to apply. Unused."""
def has_role (so, role):
    """Check if an agent has the specified role.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): The role to test for
    
    Returns:
        bool: True if the agent has that role"""
def link (set_holder, link_name: str, set_to):
    """Create a link between agents
    
    Args:
        set_holder (Agent | int | set[Agent | int]): The host (agent, id, or set) of the link
        link_name (str): The link name
        set_to (Agent | set[Agent]): The items to link to"""
def remove_role (agents, role):
    """Remove a role from an agent or a set of agents.a
    
    Args:
        agents (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def respawn_player_ship (id_or_obj):
    """Cause the specified player ship to respawn after 'destruction'.
    Args:
        id_or_obj (Agent | int): The agent or id of the player ship."""
def role (role: str):
    """Returns a set of all the agents with a given role as a set of IDs.
    
    Args:
        role (str): The role.
    
    Returns:
        set[int]: a set of agent IDs."""
def set_damage_coefficients (id_or_obj):
    """Update the damage coefficients of the ship based on the number of damaged nodes for each system.
    Assumes the standard system roles.
    Args:
        id_or_obj (Agent | int): The agent or id of the ship."""
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
def to_blob (id_or_obj):
    """Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_data_set
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
def unlink (set_holder, link_name: str, set_to):
    """Removes the link between things
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or set of agents (ids or objects)
        link_name (str): Link name
        set_to (Agent | int | set[Agent | int]): The agent or set of agents (ids or objects) to add a link to"""
