from ..agent import Agent
from .query import to_object_list, to_set, to_object, to_space_object


def role(role: str):
    """Return the set of agent IDs that currently hold a given role.

    Args:
        role (str): The role name.

    Returns:
        set[int]: IDs of all agents with that role.
    """
    return set(Agent.get_role_set(role))

def role_allies(id_or_obj):
    """Return the set of agent IDs allied with the specified object.

    Deprecated as of v1.3.0. Prefer the Sides system.

    Args:
        id_or_obj (Agent | int): The agent ID or object.

    Returns:
        set[int]: IDs of all agents on allied sides.
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
    """Return whether two objects share any allied side.

    Deprecated as of v1.3.0. Prefer the Sides system.

    Args:
        id_or_obj (Agent | int): First agent ID or object.
        other_id_or_obj (Agent | int): Second agent ID or object.

    Returns:
        bool: ``True`` if both objects have at least one allied side in common.
    """
    # TODO: This may be deprecated as the Sides system is implemented.
    a = role_allies(id_or_obj)
    if len(a)==0:
        return False
    o = role_allies(other_id_or_obj)
    t = a & o
    return len(t)>0

def role_ally_add(id_or_obj, side):
    """Add a side to an agent's ally list.

    Deprecated as of v1.3.0. Prefer the Sides system.

    Args:
        id_or_obj (Agent | int): The agent ID or object to update.
        side (str): The side name to add as an ally.
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
    """Remove a side from an agent's ally list.

    Deprecated as of v1.3.0. Prefer the Sides system.

    Args:
        id_or_obj (Agent | int): The agent ID or object to update.
        side (str): The side name to remove from the ally list.
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
    """Return the list of role names held by an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        list[str]: Role names, or an empty list if the agent does not exist.
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return []
    return obj.get_roles()

def get_role_string(id_or_obj):
    """Return a comma-separated string of role names held by an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        str: Comma-separated role names, or ``""`` if the agent does not exist.
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    return ",".join(obj.get_roles())

def any_role(roles: str):
    """Return the set of agent IDs that hold at least one of the given roles.

    Args:
        roles (str): A single role name or a comma-separated list.

    Returns:
        set[int]: IDs of agents with any of the specified roles.
    """
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret | role(r)
    return ret

def all_roles(roles: str):
    """Return the set of agent IDs that hold every one of the given roles.

    Args:
        roles (str): A comma-separated list of role names.

    Returns:
        set[int]: IDs of agents that have all specified roles.
    """
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret & role(r)
    return ret


def add_role(set_holder, role):
    """Add a role to one or more agents.

    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add.
    """
    linkers = to_object_list(to_set(set_holder))
    for so in linkers:
        so.add_role(role)

def remove_role(agents, role):
    """Remove a role from one or more agents.

    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove.
    """
    linkers = to_object_list(to_set(agents))
    for so in linkers:
        so.remove_role(role)

def has_role(so, role):
    """Return whether an agent currently holds a given role.

    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.

    Returns:
        bool: ``True`` if the agent has the role.
    """
    so = to_object(so)
    if so:
        return so.has_role(role)
    return False

def has_roles(so, roles):
    """Return whether an agent holds all of the given roles.

    Args:
        so (Agent | int): Agent ID or object.
        roles (str): A comma-separated list of role names.

    Returns:
        bool: ``True`` if the agent has every role in the list.
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
    """Return whether an agent holds at least one of the given roles.

    Args:
        so (Agent | int): Agent ID or object.
        roles (str): A comma-separated list of role names.

    Returns:
        bool: ``True`` if the agent has one or more of the roles.
    """
    so = to_object(so)
    if so:
        roles = roles.split(",")
        for role in roles:
            if so.has_role(role):
                return True
    return False
