from ..agent import Agent
from .query import to_object_list, to_set, to_object


def role(role: str):
    """returns a set of all the agents with a given role.

    Args:
        role (str): The role

    Returns:
        agent id set: a set of agent IDs
    """
    return set(Agent.get_role_set(role))

def role_allies(id_or_obj):
    """returns a set of all the ids from allies.

    Args:
        id_or_obj (id | object): The item to get allies

    Returns:
        agent id set: a set of agent IDs
    """
    ret = set()
    obj = to_object(id_or_obj)
    if obj is None or obj.id==0:
        return ret
    allies = obj.data_set.get("ally_list",0)
    ret = role(obj.side)
    if allies is None or allies=="":
        return ret
    # Make sure side is included
    items = allies.split(",")
    for _role in items:
        ret |= role(_role)
    return ret


def any_role(roles: str):
    """returns a set of all the agents with a any of the given roles.

    Args:
        role (str): The role

    Returns:
        agent id set: a set of agent IDs
    """    
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret | role(r)
    return ret

def all_roles(roles: str):
    """returns a set of all the agents with a given role.

    Args:
        roles (str): The roles comma separated 

    Returns:
        agent id set: a set of agent IDs
    """    
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret & role(r)
    return ret


def add_role(set_holder, role):
    """ add a role to a set of agents

    Args:
        set_holder (agent set): a set of IDs or 
        role (str): The role to add
    """    
    linkers = to_object_list(to_set(set_holder))
    for so in linkers:
        so.add_role(role)

def remove_role(agents, role):
    """ remove a role from a set of agents

    Args:
        agents (agent set): a set of IDs or 
        role (str): The role to add
    """    
    linkers = to_object_list(to_set(agents))
    for so in linkers:
        so.remove_role(role)

def has_role(so, role):
    """check if an agent has a role

    Args:
        so (an agent): an agent id or object
        role (str): the role to test for

    Returns:
        bool: if the agent has that role
    """    
    so = to_object(so)
    if so:
        return so.has_role(role)
    return False

def has_roles(so, roles):
    """check if an agent has all the roles specified

    Args:
        so (an agent): an agent id or object
        role (str): a string comma separated roles

    Returns:
        bool: if the agent has that role
    """        
    so = to_object(so)
    if so:
        roles = roles.split(",")
        for role in roles:
            if not so.has_role(role):
                return False
    return True


