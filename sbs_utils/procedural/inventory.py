from ..agent import Agent
from .query import to_object_list, to_set, to_object



def has_inventory(key: str):
    """ has_inventory

        get the object that have a inventory item with the given key

        :param key: The key/name of the inventory item
        :type key: str
        :rtype: set of ids
        """
    return Agent.has_inventory_set(key)
def inventory_set(link_source, link_name: str):
    """ inventory_set

        get the set that inventory items with the given key the the link source has
        this is the way to create a collection in inventory

        :param link_source: The id object to check
        :type link_source: int / id
        :param link_name: The key/name of the inventory item
        :type link_name: str
        :rtype: set of data
        """
    link_source = Agent.resolve_py_object(link_source)
    return link_source.get_inventory_set(link_name)

def inventory_value(link_source, link_name: str, default=None):
    """ inventory_value

        get the value that inventory items with the given key the the link source has
        
        :param link_source: The id object to check
        :type link_source: int / id
        :param link_name: The key/name of the inventory item
        :type link_name: str
        :rtype: data
        """
    
    link_source = Agent.resolve_py_object(link_source)
    if link_source is not None:
        return link_source.get_inventory_value(link_name, default)
    return None

def get_inventory_value(so, key, default=None):
    """ get_inventory_value

    get the value that inventory items with the given key the the link source has
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: data
    """
    so = to_object(so)
    if so is not None:
        return so.get_inventory_value(key, default)
    return default
            
def set_inventory_value(so, key, value):
    """ set_inventory_value

    set the value that inventory items with the given key the the link source has
    
    :param source: The id object to check
    :type source: int / id
    :param key: The key/name of the inventory item
    :type key: str
    :param value: The value of the inventory item
    :type value: str
    """
   
    obj_list = to_object_list(so)
    for obj in obj_list:
        if obj is not None:
            obj.set_inventory_value(key, value)

def get_shared_inventory_value(key, default=None):
    """ get_shared_inventory_value

    get the value that inventory items with the given key on the shared agent
   
    :param key: The key/name of the inventory item
    :type key: str
    :param value: The value of the inventory item
    :type value: str
    """
    return Agent.SHARED.get_inventory_value(key, default)

def set_shared_inventory_value(key, value):
    """ set_inventory_value

    set the value that inventory items with the given key on the shared agent
    
    :param key: The key/name of the inventory item
    :type key: str
    :param value: The value of the inventory item
    :type value: str
    """
    return Agent.SHARED.get_inventory_value(key, value)