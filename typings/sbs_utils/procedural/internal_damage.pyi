from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def add_role (set_holder, role):
    """add a role to a set of agents
    
    Args:
        set_holder (agent set): a set of IDs or
        role (str): The role to add"""
def all_roles (roles: str):
    """returns a set of all the agents with a given role.
    
    Args:
        roles (str): The roles comma separated
    
    Returns:
        agent id set: a set of agent IDs"""
def comms_broadcast (ids_or_obj, msg, color=None) -> None:
    """Send text to the text waterfall
    The ids can be player ship ids or client/console ids
    
    Args:
        ids_or_obj (id or objecr): A set or single id or object to send to,
        msg (str): The text to send
        color (str, optional): The Color for the text. Defaults to "#fff"."""
def convert_system_to_string (the_system):
    ...
def explode_player_ship (id_or_obj):
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def get_pos (id_or_obj):
    """get the position of an agent
    
    Args:
        id_or_obj (agent id | agent): The agent to set position on
    
    Returns:
        Vec3: _description_"""
def grid_apply_system_damage (id_or_obj):
    ...
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj_or_set (agent set): The agent
        target_set (agent set, optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (_type_, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_count_grid_data (ship_key, role, default):
    """Count the amount of grid items with the give role(from the json data)
    for the given ship """
def grid_damage_grid_object (ship_id, grid_id, damage_color):
    ...
def grid_damage_hallway (id_or_obj, loc_x, loc_y, damage_color):
    ...
def grid_damage_pos (id_or_obj, loc_x, loc_y):
    ...
def grid_damage_system (id_or_obj, the_system):
    """grid_damage_system
    
    damage a system using the grid objects of the ship
    
    :param id_or_obj: the ship to damage
    :type id_oe_obj: int, obj, close_data, spawn_data
    :param the_system: The system to damage, None picks random
    :type: string, int, sbs.SHPSYS
    :rtype: bool if a system was found to be damaged"""
def grid_get_grid_current_theme ():
    ...
def grid_get_grid_data ():
    """get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid data objects key is a ship key"""
def grid_get_item_theme_data (roles, name=None):
    ...
def grid_get_max_hp ():
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
def grid_rebuild_grid_objects (id_or_obj, grid_data=None):
    ...
def grid_repair_grid_objects (player_ship, id_or_set, who_repaired=None):
    ...
def grid_repair_system_damage (id_or_obj, the_system=None):
    ...
def grid_restore_damcons (id_or_obj):
    ...
def grid_set_max_hp (max_hp):
    ...
def grid_spawn (id, name, tag, x, y, icon, color, roles):
    """Spawn a grid object on a ship
    
    Args:
        id (agent): The agent to add the grid object to
        name (str): The name of the grid item
        tag (str): The tag/side
        x (int): the x grid location
        y (int): the y grid location
        icon (int): the icon index
        color (str): color
        roles (str): string of comma separated roles
    
    Returns:
        GridObject: The grid object"""
def grid_take_internal_damage_at (id_or_obj, source_point, system_hit, damage_amount):
    ...
def has_role (so, role):
    """check if an agent has a role
    
    Args:
        so (an agent): an agent id or object
        role (str): the role to test for
    
    Returns:
        bool: if the agent has that role"""
def link (set_holder, link, set_to):
    """create a link between agents
    
    Args:
        set_holder (agent | agent set): The host (set) of the link
        link (str): The link name
        set_to (agent|agent set): The items to link to"""
def remove_role (agents, role):
    """remove a role from a set of agents
    
    Args:
        agents (agent set): a set of IDs or
        role (str): The role to add"""
def respawn_player_ship (id_or_obj):
    ...
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def set_damage_coefficients (id_or_obj):
    ...
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def signal_emit (name, data=None):
    ...
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
def unlink (set_holder, link, set_to):
    """removes the link between things
    
    Args:
        set_holder (agent|agent set): An agent or set of agents (ids or objects)
        link (str): Link name
        set_to (agent|agent set): The agents(s) to add a link to"""
