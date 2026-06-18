from ..agent import Agent
from .query import to_object_list, to_set, to_object



def has_inventory(key: str):
    """Return the set of agent IDs that have an inventory entry for the given key.

    Args:
        key (str): The inventory key to look for.

    Returns:
        set[int]: IDs of all agents that have this key set.
    """
    return Agent.has_inventory_set(key)

def has_inventory_value(key: str, value):
    """Return the set of agent IDs whose inventory value for ``key`` equals ``value``.

    Args:
        key (str): The inventory key to look for.
        value: The exact value to match.

    Returns:
        set[int]: IDs of agents whose ``key`` inventory entry equals ``value``.
    """
    holders = Agent.has_inventory_set(key)
    ret = set()
    for holder in to_object_list(holders):
        v = holder.get_inventory_value(key)
        if v == value:
            ret.add(holder.get_id())
    return ret

def inventory_set(source, key: str):
    """Return the set stored in an agent's inventory under ``key``.

    Used to treat an inventory entry as a collection. The value stored under
    ``key`` is expected to be a set; use ``set_inventory_value`` to write it.

    Args:
        source (Agent | int): The agent ID or object.
        key (str): The inventory key.

    Returns:
        set: The set stored in inventory, or an empty set if not present.
    """
    source = Agent.resolve_py_object(source)
    return source.get_inventory_set(key)


def get_inventory_value(id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.

    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.

    Returns:
        any: The inventory value, or ``default`` if the key is not set.
    """
    if id_or_object != 0:
        id_or_object = to_object(id_or_object)
    else:
        id_or_object = Agent.get(0)
        
    if id_or_object is not None:
        return id_or_object.get_inventory_value(key, default)
    return default

def inventory_value(id_or_obj, key: str, default=None):
    """Get an inventory value from an agent by key (alias for ``get_inventory_value``).

    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.

    Returns:
        any: The inventory value, or ``default`` if the key is not set.
    """
    return get_inventory_value(id_or_obj, key, default)

            
def set_inventory_value(so, key: str, value):
    """Set an inventory value on one or more agents.

    If ``so`` is a set or collection, every member receives the value.

    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store.
    """
    obj_list = to_object_list(so)
    for obj in obj_list:
        if obj is not None:
            obj.set_inventory_value(key, value)

def remove_inventory_value(so, key):
    """Remove an inventory key from one or more agents.

    If ``so`` is a set or collection, the key is removed from every member.

    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key to remove.
    """
    obj_list = to_object_list(so)
    for obj in obj_list:
        if obj is not None:
            obj.set_inventory_value(key) # Value not specified, so None

def get_shared_inventory_value(key, default=None):
    """Get an inventory value from the global shared agent.

    Args:
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.

    Returns:
        any: The shared inventory value, or ``default`` if not set.
    """
    return Agent.SHARED.get_inventory_value(key, default)

def set_shared_inventory_value(key, value):
    """Set an inventory value on the global shared agent.

    Args:
        key (str): The inventory key.
        value (any): The value to store.
    """
    return Agent.SHARED.set_inventory_value(key, value)
