from sbs_utils.engineobject import EngineObject
def get_inventory_value (so, link, default=None):
    ...
def has_inventory (key: str):
    """has_inventory
    
    get the object that have a inventory item with the given key
    
    :param key: The key/name of the inventory item
    :type key: str
    :rtype: set of ids"""
def inventory_set (link_source, link_name: str):
    """inventory_set
    
    get the set that inventory items with the given key the the link source has
    this is the way to create a collection in inventory
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: set of data"""
def inventory_value (link_source, link_name: str, default=None):
    """inventory_value
    
    get the value that inventory items with the given key the the link source has
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: data"""
def set_inventory_value (so, name, value):
    ...
def to_object (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_object_list (the_set):
    """to_object_list
    
    converts a set to a list of objects
    
    :param the_set: A set of ids
    :type the_set: set of ids
    
    :rtype: list of EngineObject"""
def to_set (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_set
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
