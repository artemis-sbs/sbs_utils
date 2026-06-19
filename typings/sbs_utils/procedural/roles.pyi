from sbs_utils.agent import Agent
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def all_roles (roles: str):
    """Return the set of agent IDs that hold every one of the given roles.
    
    Args:
        roles (str): A comma-separated list of role names.
    
    Returns:
        set[int]: IDs of agents that have all specified roles."""
def any_role (roles: str):
    """Return the set of agent IDs that hold at least one of the given roles.
    
    Args:
        roles (str): A single role name or a comma-separated list.
    
    Returns:
        set[int]: IDs of agents with any of the specified roles."""
def get_role_list (id_or_obj):
    """Return the list of role names held by an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        list[str]: Role names, or an empty list if the agent does not exist."""
def get_role_string (id_or_obj):
    """Return a comma-separated string of role names held by an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: Comma-separated role names, or ``""`` if the agent does not exist."""
def has_any_role (so, roles):
    """Return whether an agent holds at least one of the given roles.
    
    Args:
        so (Agent | int): Agent ID or object.
        roles (str): A comma-separated list of role names.
    
    Returns:
        bool: ``True`` if the agent has one or more of the roles."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def has_roles (so, roles):
    """Return whether an agent holds all of the given roles.
    
    Args:
        so (Agent | int): Agent ID or object.
        roles (str): A comma-separated list of role names.
    
    Returns:
        bool: ``True`` if the agent has every role in the list."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def role_allies (id_or_obj):
    """Return the set of agent IDs allied with the specified object.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
    
    Returns:
        set[int]: IDs of all agents on allied sides."""
def role_ally_add (id_or_obj, side):
    """Add a side to an agent's ally list.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object to update.
        side (str): The side name to add as an ally."""
def role_ally_remove (id_or_obj, side):
    """Remove a side from an agent's ally list.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object to update.
        side (str): The side name to remove from the ally list."""
def role_are_allies (id_or_obj, other_id_or_obj):
    """Return whether two objects share any allied side.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): First agent ID or object.
        other_id_or_obj (Agent | int): Second agent ID or object.
    
    Returns:
        bool: ``True`` if both objects have at least one allied side in common."""
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
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).
    
    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The space-object agent, or ``None``."""
