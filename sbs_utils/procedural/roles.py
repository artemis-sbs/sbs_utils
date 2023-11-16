from ..agent import Agent
from .query import to_object_list, to_set, to_object

def role(role: str):
    """ role

        returns a set of all the engine objects with a given role.

        :param role: the role
        :type role: str
        
        :rtype: set of ids 
    """
    return Agent.get_role_set(role)

def any_role(roles: str):
    """ role

        returns a set of all the engine objects with a given role.

        :param role: the role
        :type role: str
        
        :rtype: set of ids 
    """
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret | role(r)
    return ret

def all_roles(roles: str):
    """ role

        returns a set of all the engine objects with a given role.

        :param role: the role
        :type role: str
        
        :rtype: set of ids 
    """
    roles = roles.split(",")
    if len(roles)==0:
        return set()
    ret = role(roles[0])
    for r in roles[1:]:
        ret = ret & role(r)
    return ret


def add_role(set_holder, role):
    linkers = to_object_list(to_set(set_holder))
    for so in linkers:
        so.add_role(role)

def remove_role(set_holder, role):
    linkers = to_object_list(to_set(set_holder))
    for so in linkers:
        so.remove_role(role)

def has_role(so, role):
    so = to_object(so)
    if so:
        return so.has_role(role)
    return False

def has_roles(so, roles):
    so = to_object(so)
    if so:
        roles = roles.split(",")
        for role in roles:
            if not so.has_role(role):
                return False
    return True

def get_race(id_or_obj):
    races = ["kralien", "arvonian", "torgoth", "skaraan", "ximni"]
    for test in races:
        if has_role(id_or_obj, test):
            return test
    return None
