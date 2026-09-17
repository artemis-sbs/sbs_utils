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
def to_agent_list (the_set):
    """Resolve to Agent objects for a WRITE, the SERVER CONSOLE included.
    
    `to_object` refuses id 0 by design - 0 means "no object" for a space object - so
    every write built on :func:`to_object_list` silently skipped the server console.
    That is not a corner case: the server window is a console like any other, and
    `add_role(client_id, "console, mainscreen")` on it was a no-op, which is why an
    overlay narrowed with `consoles="mainscreen"` never reached the main screen when
    the main screen WAS the server.
    
    The reads already knew better - `get_inventory_value` has carried an explicit
    `Agent.get(0)` branch for exactly this. This is that branch generalized, so a write
    can reach everything a read can see.
    
    Space-object callers keep using `to_object_list`: id 0 there really does mean "no
    object", and this must not resurrect it for them.
    
    Args:
        the_set (set[Agent | int] | list[Agent | int] | Agent | int): what to resolve.
    
    Returns:
        list[Agent]: resolved agents; unresolvable entries are dropped."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
