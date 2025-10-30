def get_data_set_value (id_or_obj, key, index=0):
    """Get the data set (blob) value for the object with the given key.
    Args:
        id_or_obj (Agent | int): The agent or id.
        key (str): The data set key
        index (int, optional): The index of the data set value
    Returns:
        any: The value associated with the key and index."""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def has_role (so, role):
    """Check if an agent has the specified role.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): The role to test for
    
    Returns:
        bool: True if the agent has that role"""
def role (role: str):
    """Returns a set of all the agents with a given role as a set of IDs.
    
    Args:
        role (str): The role.
    
    Returns:
        set[int]: a set of agent IDs."""
def set_data_set_value (to_update, key, value, index=0):
    """Set the data set (blob) value for the objects with the given key. If `to_update` is a set or list, sets the data set value for each object.
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The agent or id or set or list.
        key (str): The data set key.
        value (any): The value to assign.
        index (int, optional): The index of the data set value"""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def side_ally_members_set (side):
    """Get a set of all space objects allied with the side.
    Args:
        side (str | int | Agent): The id or key of the side, or the id or object of a spaceobject.
    Returns:
        set[int]: A set containing the ids of all allied ships, stations, etc."""
def side_are_allies (side1, side2) -> bool:
    """Check if the specified sides are allies.
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns:
        True if they are allies, otherwise False"""
def side_are_enemies (side1, side2) -> bool:
    """Check if the specified sides are enemies.
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns:
        True if they are allies, otherwise False"""
def side_are_neutral (side1, side2) -> bool:
    """Check if the specified sides are neutral (neither enemies nor allies).
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns:
        True if they are allies, otherwise False"""
def side_display_name (key):
    """Get the display name of the side.
    
    Args:
        key (str | int): The key or id of the side.
    Returns:
        str: The display name of the side."""
def side_enemy_members_set (side):
    """Get a set of all space objects that are enemies of the side.
    Args:
        side (str | int | Agent): The id or key of the side, or the id or object of a spaceobject.
    Returns:
        set[int]: A set containing the ids of all enemy ships, stations, etc."""
def side_get_relations (side1, side2):
    """Get the relations value of the two sides.
    * 1: Allies
    * 0: Neutral
    * -1: Enemies
    
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns:
        int: relations value"""
def side_keys_set ():
    """Get a set containing the keys for all existing sides.
    
    Returns:
        set[str]: A set of keys for all sides."""
def side_members_set (side):
    """Get all objects with the specified side. Use this instead of `role(side)`.
    
    Args:
        side (str | int | Agent): The key or name of the side, or the ID of the side, or the side object, or an object with the given side.
    
    Returns:
        set[int]: Set of ids with the specified side."""
def side_set_relations (side1, side2, relation):
    """Update relations between two sides, and update the ally and hostile lists for all their members.
    
    Args:
        side1 (str|int): key or id of the first side
        side2 (str|int): key or id of the second side
        relation (int): the new relations between the sides.
            * 1: Ally
            * 0: Netural
            * -1: Enemy"""
def side_set_ship_allies_and_enemies (ship):
    """Generate the ally list and hostile list for the specified ship based on its side.
    Args:
        ship (Agent | int): The object for which the ally and hostile lists should be updated."""
def sides_set ():
    """Get a set containing the ids of all sides (objects with the "__side__" role).
    
    Returns:
        set[int]: A set of IDs for each side."""
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
def to_side_id (key_or_id_or_object):
    """Get the id for the given side.
    
    Args:
        key_or_id (str | int): the key or the Agent of the side, or the id or Agent of a space object.
    
    Returns:
        int | None: The ID of the side. If the key, name, or id doesn't exist, returns None."""
def to_side_object (key_or_id):
    """Get the object for the given side.
    
    Args:
        key_or_id (str | int): the key or the Agent ID of the side, or an Agent or Agent ID belonging to the side.
    
    Returns:
        Agent|None: The Agent object for the side. If the key, agent, or id doesn't exist, returns None."""
