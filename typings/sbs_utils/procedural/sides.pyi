def get_data_set_value (id_or_obj, key, index=0):
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def has_role (so, role):
    """check if an agent has a role
    
    Args:
        so (an agent): an agent id or object
        role (str): the role to test for
    
    Returns:
        bool: if the agent has that role"""
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def set_data_set_value (to_update, key, value, index=0):
    ...
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def side_ally_members_set (side):
    """Get a set of all space objects allied with the side
    Args:
        side (str|int|Agent): The id or key of the side, or the id or object of a spaceobject
    Returns:
        Set: A set containing the ids of all allied ships, stations, etc."""
def side_are_allies (side1, side2) -> bool:
    """Check if the specified sides are allies.
    Args:
        side1 (str|int): the key or id of the first side
        side2 (str|int): the key or id of the second side
    Returns:
        True if they are allies, otherwise False"""
def side_are_enemies (side1, side2) -> bool:
    """Check if the specified sides are enemies.
    Args:
        side1 (str|int): the key or id of the first side
        side2 (str|int): the key or id of the second side
    Returns:
        True if they are allies, otherwise False"""
def side_are_neutral (side1, side2) -> bool:
    """Check if the specified sides are neutral (neither enemies nor allies).
    Args:
        side1 (str|int): the key or id of the first side
        side2 (str|int): the key or id of the second side
    Returns:
        True if they are allies, otherwise False"""
def side_display_name (key):
    """Get the display name of the side.
    
    Args:
        key (str|int): The key or id of the side
    Returns:
        str: The display name of the side"""
def side_enemy_members_set (side):
    """Get a set of all space objects that are enemies of the side
    Args:
        side (str|int|Agent): The id or key of the side, or the id or object of a spaceobject
    Returns:
        Set: A set containing the ids of all enemy ships, stations, etc."""
def side_keys_set ():
    """Get a set containing the keys for all existing sides.
    
    Returns:
        Set: A set of keys for all sides"""
def side_members_set (side):
    """Get all objects with the specified side. Use this instead of `role(side)`
    
    Args:
        side (str|int|Agent): The key or name of the side, or the ID of the side, or the side object, or an object with the given side
    
    Returns:
        Set of ids with the specified side."""
def side_set_relations (side1, side2, relation):
    """Update relations between two sides
    
    Args:
        side1 (str|int): key or id of the first side
        side2 (str|int): key or id of the second side
        relation (int): the new relations between the sides.
            1: Ally
            0: Netural
            -1: Enemy"""
def side_set_ship_allies_and_enemies (ship):
    ...
def sides_set ():
    """Get a set containing the ids of all sides (objects with the "__side__" role).
    
    Returns:
        Set: A set of IDs for each side"""
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
def to_side_id (key_or_id_or_object):
    """Get the id for the given side
    
    Args:
        key_or_id (str|int): the key or the Agent of the side, or the id or Agent of a space object
    
    Returns:
        int|None: The ID of the side. If the key, name, or id doesn't exist, returns None."""
def to_side_object (key_or_id):
    """Get the object for the given side
    
    Args:
        key_or_id (str|int): the key or the Agent ID of the side, or an Agent or Agent ID belonging to the side
    
    Returns:
        Agent|None: The Agent object for the side. If the key, agent, or id doesn't exist, returns None."""
