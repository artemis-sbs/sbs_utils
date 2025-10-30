from sbs_utils.agent import Agent
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_shared_inventory_value (key, default=None):
    """Get inventory value from the shared data agent.
    
    Args:
        key (str): The key/name of the inventory item
        default (any): the value to return if not found"""
def has_inventory (key: str):
    """get the set of agent ids that have a inventory item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set[int]: set of ids"""
def has_inventory_value (key: str, value):
    """Get the object that have a inventory item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set[int]: set of ids"""
def inventory_set (source, key: str):
    """Get the set that inventory items with the given key the the link source has
        this is the way to create a collection in inventory
    
    !!! Note
        This is like set_inventory_value but the value is a set
    
    Args:
        source (Agent): The agent id or object to check
        key (str): The key/name of the inventory item
        set[any]: set of data"""
def inventory_value (id_or_obj, key: str, default=None):
    """Get inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def remove_inventory_value (so, key):
    """Remove a value from the agent's inventory.
    `so` can be a set. If it is, the value is removed from the inventory of each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def set_shared_inventory_value (key, value):
    """Set inventory value with the given key on the shared agent.
    
    Args:
        key (str): The key/name of the inventory item
        value (any): the value"""
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
