from sbs_utils.agent import Agent
def add_role (set_holder, role):
    """Add a role to an agent or a set of agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def all_roles (roles: str):
    """Returns a set of all the agents which have all of the given roles.
    
    Args:
        roles (str): A comma-separated list of roles.
    
    Returns:
        set[int]: a set of agent IDs."""
def any_role (roles: str):
    """Returns a set of all the agents which have any of the given roles.
    
    Args:
        role (str): The role, or a comma-separated list of roles.
    
    Returns:
        set[int]: a set of agent IDs."""
def get_role_list (id_or_obj):
    """Returns a list of role names an Agent has.
    
    Args:
        id_or_obj (Agent | int): The object or ID.
    
    Returns:
        list[str]: The list of roles."""
def get_role_string (id_or_obj):
    """Returns a comma-separated list of role names an Agent has.
    
    Args:
        id_or_obj (Agent | int): The Agent or id.
    
    Returns:
        str: A comma-separated string."""
def has_any_role (so, roles):
    """Check if an agent has any of the roles specified.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): A comma-separated list of roles.
    
    Returns:
        bool: True if the agent has one or more of the roles."""
def has_role (so, role):
    """Check if an agent has the specified role.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): The role to test for
    
    Returns:
        bool: True if the agent has that role"""
def has_roles (so, roles):
    """Check if an agent has all the roles specified.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): A comma-separated list of roles.
    
    Returns:
        bool: True if the agent has all the listed roles."""
def remove_role (agents, role):
    """Remove a role from an agent or a set of agents.a
    
    Args:
        agents (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def role (role: str):
    """Returns a set of all the agents with a given role as a set of IDs.
    
    Args:
        role (str): The role.
    
    Returns:
        set[int]: a set of agent IDs."""
def role_allies (id_or_obj):
    """Returns a set of the IDs of all objects allied with the specified object.
    
    Args:
        id_or_obj (Agent | int): The object for which to get the allies.
    
    Returns:
        set[int]: a set of agent IDs"""
def role_ally_add (id_or_obj, side):
    """Adds a side as an ally and add all the objects with that side to the specified object's ally list.
    
    Args:
        id_or_obj (Agent | int): The object for which to add allies.
        side (str): The side string."""
def role_ally_remove (id_or_obj, side):
    """Remove a side as an ally and remove all objects of that side from the specified object's ally list.
    
    Args:
        id_or_obj (Agent | int): The object from which to remove allies.
        side (str): The side string."""
def role_are_allies (id_or_obj, other_id_or_obj):
    """Check if the two objects are allied.
    
    Args:
        id_or_obj (Agent | int): The first object.
        other_id_or_obj (Agent | int): The second object.
    Returns:
        bool: True if they are allied."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def to_object_list (the_set):
    """Converts a set to a list of objects
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[Agent]: A list of Agent objects"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a set of ids
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        set[Agent | CloseData | int]: A set containing whatever was passed in."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Converts the item passed to an gui client
    ??? note
    * Retrun of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
