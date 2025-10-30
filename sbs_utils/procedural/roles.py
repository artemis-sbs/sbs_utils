from ..agent import Agent
from .query import to_object_list, to_set, to_object, to_space_object


def role(role: str):
    """
    Returns a set of all the agents with a given role as a set of IDs.

    Args:
        role (str): The role.

    Returns:
        set[int]: a set of agent IDs.
    """
    return set(Agent.get_role_set(role))

def role_allies(id_or_obj):
    """
    Returns a set of the IDs of all objects allied with the specified object.

    Args:
        id_or_obj (Agent | int): The object for which to get the allies.

    Returns:
        set[int]: a set of agent IDs
    """
    # TODO: This may be deprecated as the Sides system is implemented.
    ret = set()
    obj = to_space_object(id_or_obj)
    if obj is None or obj.id==0:
        return ret
    allies = obj.data_set.get("ally_list",0)
    ret = role(obj.side)
    if allies is None or allies=="" or allies==0:
        return ret
    # Make sure side is included
    items = allies.split(",")
    for _role in items:
        ret |= role(_role)
    return ret

def role_are_allies(id_or_obj, other_id_or_obj):
    """
    Check if the two objects are allied.
    
    Args:
        id_or_obj (Agent | int): The first object.
        other_id_or_obj (Agent | int): The second object.
    Returns:
        bool: True if they are allied.
    """
    # TODO: This may be deprecated as the Sides system is implemented.
    a = role_allies(id_or_obj)
    if len(a)==0:
        return False
    o = role_allies(other_id_or_obj)
    t = a & o
    return len(t)>0

def role_ally_add(id_or_obj, side):
    """
    Adds a side as an ally and add all the objects with that side to the specified object's ally list.

    Args:
        id_or_obj (Agent | int): The object for which to add allies.
        side (str): The side string.
    """
    # TODO: This may be deprecated as the Sides system is implemented.
    side = side.strip().lower()
    ret = set()
    obj = to_object(id_or_obj)
    if obj is None or obj.id==0:
        return ret
    
    allies = obj.data_set.get("ally_list",0)
    if allies is None or allies=="":
        allies = side
    # Make sure side is included
    items = set(allies.split(","))
    items.add(side)
    allies = ",".join(items)
    obj.data_set.set("ally_list",allies, 0)

def role_ally_remove(id_or_obj, side):
    """
    Remove a side as an ally and remove all objects of that side from the specified object's ally list.

    Args:
        id_or_obj (Agent | int): The object from which to remove allies.
        side (str): The side string.
    """
    # TODO: This may be deprecated as the Sides system is implemented.
    side = side.strip().lower()
    ret = set()
    obj = to_object(id_or_obj)
    if obj is None or obj.id==0:
        return ret
    allies = obj.data_set.get("ally_list",0)
    if allies is None or allies=="":
        return
    # Make sure side is included
    items = set(allies.split(","))
    items = [x for x in items if x != side]
    allies = ",".join(items)
    obj.data_set.set("ally_list", allies, 0)

def get_role_list(id_or_obj):
    """
    Returns a list of role names an Agent has.

    Args:
        id_or_obj (Agent | int): The object or ID.

    Returns:
        list[str]: The list of roles.
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return []
    return obj.get_roles()

def get_role_string(id_or_obj):
    """
    Returns a comma-separated list of role names an Agent has.

    Args:
        id_or_obj (Agent | int): The Agent or id.

    Returns:
        str: A comma-separated string.
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    return ",".join(obj.get_roles())

def any_role(roles: str):
    """
    Returns a set of all the agents which have any of the given roles.

    Args:
        role (str): The role, or a comma-separated list of roles.

    Returns:
        set[int]: a set of agent IDs.
    """    
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret | role(r)
    return ret

def all_roles(roles: str):
    """
    Returns a set of all the agents which have all of the given roles.

    Args:
        roles (str): A comma-separated list of roles.

    Returns:
        set[int]: a set of agent IDs.
    """    
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret & role(r)
    return ret


def add_role(set_holder, role):
    """ 
    Add a role to an agent or a set of agents.

    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add.
    """    
    linkers = to_object_list(to_set(set_holder))
    for so in linkers:
        so.add_role(role)

def remove_role(agents, role):
    """ 
    Remove a role from an agent or a set of agents.a

    Args:
        agents (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add.
    """    
    linkers = to_object_list(to_set(agents))
    for so in linkers:
        so.remove_role(role)

def has_role(so, role):
    """
    Check if an agent has the specified role.

    Args:
        so (Agent | int): An agent or id.
        role (str): The role to test for

    Returns:
        bool: True if the agent has that role
    """    
    so = to_object(so)
    if so:
        return so.has_role(role)
    return False

def has_roles(so, roles):
    """
    Check if an agent has all the roles specified.

    Args:
        so (Agent | int): An agent or id.
        role (str): A comma-separated list of roles.

    Returns:
        bool: True if the agent has all the listed roles.
    """        
    so = to_object(so)
    if so is None:
        return False
    if so:
        roles = roles.split(",")
        for role in roles:
            if not so.has_role(role):
                return False
    return True

def has_any_role(so, roles):
    """
    Check if an agent has any of the roles specified.

    Args:
        so (Agent | int): An agent or id.
        role (str): A comma-separated list of roles.

    Returns:
        bool: True if the agent has one or more of the roles.
    """        
    so = to_object(so)
    if so:
        roles = roles.split(",")
        for role in roles:
            if so.has_role(role):
                return True
    return False
