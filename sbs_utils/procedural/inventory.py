from ..agent import Agent
from .query import to_object_list, to_set, to_object



def has_inventory(key: str):
    """ get the set of agent ids that have a inventory item with the given key

    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set: set of ids
    """
    return Agent.has_inventory_set(key)

def has_inventory_value(key: str, value):
    """get the object that have a inventory item with the given key

    Args:
        key (str): The key/name of the inventory item

    Returns:
        set: set of ids
    """
    holders = Agent.has_inventory_set(key)
    ret = set()
    for holder in to_object_list(holders):
        v = holder.get_inventory_value(key)
        if v == value:
            ret.add(holder.get_id())
    return ret

def inventory_set(source, key: str):
    """ get the set that inventory items with the given key the the link source has
        this is the way to create a collection in inventory

    !!! Note
        This is like set_inventory_value bu the value is a set
        
    Args:
        source (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        set: set of data
    """
    source = Agent.resolve_py_object(source)
    return source.get_inventory_set(key)


def get_inventory_value(id_or_object, key, default=None):
    """ get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
        
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    """
    id_or_object = to_object(id_or_object)
    if id_or_object is not None:
        return id_or_object.get_inventory_value(key, default)
    return default

def inventory_value(id_or_obj, key: str, default=None):
    """ get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
        
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    """
    return get_inventory_value(id_or_obj, key, default)

            
def set_inventory_value(so, key, value):
    """ set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
        
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value
    """
    obj_list = to_object_list(so)
    for obj in obj_list:
        if obj is not None:
            obj.set_inventory_value(key, value)

def get_shared_inventory_value(key, default=None):
    """ get inventory value from the shared data agent
        
    Args:
        key (str): The key/name of the inventory item
        default (any): the value to return if not found
    """
    return Agent.SHARED.get_inventory_value(key, default)

def set_shared_inventory_value(key, value):
    """ set inventory value with the given key on the shared agent
        
    Args:
        key (str): The key/name of the inventory item
        value (any): the value
    """
    return Agent.SHARED.get_inventory_value(key, value)
