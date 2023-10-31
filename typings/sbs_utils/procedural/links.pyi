from sbs_utils.engineobject import EngineObject
def get_dedicated_link (so, link):
    ...
def has_link (key: str):
    """has_link
    
    get the object that have a link item with the given key
    
    :param key: The key/name of the inventory item
    :type key: str
    :rtype: set of ids"""
def has_link_to (link_source, link_name: str, link_target):
    """has_linked_to
    
    check if target and source are linked to for the given key
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: set of ids"""
def link (set_holder, link, set_to):
    ...
def linked_to (link_source, link_name: str):
    """linked_to
    
    get the set that inventor the source is linked to for the given key
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: set of ids"""
def set_dedicated_link (so, link, to):
    ...
def to_id (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_id_list (the_set):
    """to_id_list
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
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
def unlink (set_holder, link, set_to):
    ...
