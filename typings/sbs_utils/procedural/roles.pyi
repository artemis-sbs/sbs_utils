from sbs_utils.engineobject import EngineObject
def add_role (set_holder, role):
    ...
def all_roles (roles: str):
    """role
    
    returns a set of all the engine objects with a given role.
    
    :param role: the role
    :type role: str
    
    :rtype: set of ids """
def any_role (roles: str):
    """role
    
    returns a set of all the engine objects with a given role.
    
    :param role: the role
    :type role: str
    
    :rtype: set of ids """
def get_race (id_or_obj):
    ...
def has_role (so, role):
    ...
def has_roles (so, roles):
    ...
def remove_role (set_holder, role):
    ...
def role (role: str):
    """role
    
    returns a set of all the engine objects with a given role.
    
    :param role: the role
    :type role: str
    
    :rtype: set of ids """
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
