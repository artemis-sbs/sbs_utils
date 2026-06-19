from sbs_utils.agent import Agent
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_shared_inventory_value (key, default=None):
    """Get an inventory value from the global shared agent.
    
    Args:
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The shared inventory value, or ``default`` if not set."""
def has_inventory (key: str):
    """Return the set of agent IDs that have an inventory entry for the given key.
    
    Args:
        key (str): The inventory key to look for.
    
    Returns:
        set[int]: IDs of all agents that have this key set."""
def has_inventory_value (key: str, value):
    """Return the set of agent IDs whose inventory value for ``key`` equals ``value``.
    
    Args:
        key (str): The inventory key to look for.
        value: The exact value to match.
    
    Returns:
        set[int]: IDs of agents whose ``key`` inventory entry equals ``value``."""
def inventory_set (source, key: str):
    """Return the set stored in an agent's inventory under ``key``.
    
    Used to treat an inventory entry as a collection. The value stored under
    ``key`` is expected to be a set; use ``set_inventory_value`` to write it.
    
    Args:
        source (Agent | int): The agent ID or object.
        key (str): The inventory key.
    
    Returns:
        set: The set stored in inventory, or an empty set if not present."""
def inventory_value (id_or_obj, key: str, default=None):
    """Get an inventory value from an agent by key (alias for ``get_inventory_value``).
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def remove_inventory_value (so, key):
    """Remove an inventory key from one or more agents.
    
    If ``so`` is a set or collection, the key is removed from every member.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key to remove."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def set_shared_inventory_value (key, value):
    """Set an inventory value on the global shared agent.
    
    Args:
        key (str): The inventory key.
        value (any): The value to store."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
