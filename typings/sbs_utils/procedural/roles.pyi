from sbs_utils.agent import Agent
def add_role (set_holder, role):
    """add a role to a set of agents
    
    Args:
        set_holder (agent set): a set of IDs or
        role (str): The role to add"""
def all_roles (roles: str):
    """returns a set of all the agents with a given role.
    
    Args:
        roles (str): The roles comma separated
    
    Returns:
        agent id set: a set of agent IDs"""
def any_role (roles: str):
    """returns a set of all the agents with a any of the given roles.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def get_role_list (id_or_obj):
    """Returns a list of role names an Agent has
    
    Args:
        id_or_obj (int | obj): The Agent to
    
    Returns:
        list[str]: The list of role"""
def get_role_string (id_or_obj):
    """Returns a comma separated list of role names an Agent has
    
    Args:
        id_or_obj (int | obj): The Agent to
    
    Returns:
        str: The a comma separated string"""
def has_any_role (so, roles):
    """check if an agent has any the roles specified
    
    Args:
        so (an agent): an agent id or object
        role (str): a string comma separated roles
    
    Returns:
        bool: if the agent has that role"""
def has_role (so, role):
    """check if an agent has a role
    
    Args:
        so (an agent): an agent id or object
        role (str): the role to test for
    
    Returns:
        bool: if the agent has that role"""
def has_roles (so, roles):
    """check if an agent has all the roles specified
    
    Args:
        so (an agent): an agent id or object
        role (str): a string comma separated roles
    
    Returns:
        bool: if the agent has that role"""
def remove_role (agents, role):
    """remove a role from a set of agents
    
    Args:
        agents (agent set): a set of IDs or
        role (str): The role to add"""
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def role_allies (id_or_obj):
    """returns a set of all the ids from allies.
    
    Args:
        id_or_obj (id | object): The item to get allies
    
    Returns:
        agent id set: a set of agent IDs"""
def role_ally_add (id_or_obj, side):
    """adds an side as an ally
    
    Args:
        id_or_obj (id | object): The item to get allies
        side (str): The side string"""
def role_ally_remove (id_or_obj, side):
    """adds an side as an ally
    
    Args:
        id_or_obj (id | object): The item to get allies
        side (str): The side string"""
def role_are_allies (id_or_obj, other_id_or_obj):
    ...
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def to_object_list (the_set):
    """to_object_list
    converts a set to a list of objects
    
    Args:
        the_set (set|list): a set of agent ids
    
    Returns:
        list: of Agents"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a set of ids
    
    Args:
        the_set (set): set, list or single item
    
    Returns:
        set of things"""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """converts the item passed to an gui client
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
