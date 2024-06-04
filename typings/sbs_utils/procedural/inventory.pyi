from sbs_utils.agent import Agent
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def get_shared_inventory_value (key, default=None):
    """get inventory value from the shared data agent
    
    Args:
        key (str): The key/name of the inventory item
        default (any): the value to return if not found"""
def has_inventory (key: str):
    """get the set of agent ids that have a inventory item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set: set of ids"""
def has_inventory_value (key: str, value):
    """get the object that have a inventory item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set: set of ids"""
def inventory_set (source, key: str):
    """get the set that inventory items with the given key the the link source has
        this is the way to create a collection in inventory
    
    !!! Note
        This is like set_inventory_value bu the value is a set
    
    Args:
        source (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        set: set of data"""
def inventory_value (id_or_obj, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def set_shared_inventory_value (key, value):
    """set inventory value with the given key on the shared agent
    
    Args:
        key (str): The key/name of the inventory item
        value (any): the value"""
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
