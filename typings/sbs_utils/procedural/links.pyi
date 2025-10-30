from sbs_utils.agent import Agent
def get_dedicated_link (so, link_name: str):
    """Get the agent linked to the specified agent.
    
    !!! Note
        Dedicated link means there is only one thing linked to 1-1
    
    Args:
        link_name (str): The link name
    
    Returns:
        int | None: The id of a single agent or None"""
def has_link (link_name: str):
    """Get the objects that have a link item with the given key.
    
    Args:
        link_name (str): The key/name of the link
    
    Returns:
        set[int]: set of ids"""
def has_link_to (link_source, link_name: str, link_target):
    """check if target and source are linked to for the given key
    
    Args:
        link_source (Agent | int): The agent or id hosting the link
        link_name (str): The key/name of the inventory item
    
    Returns:
        set[int]: The set of linked ids"""
def link (set_holder, link_name: str, set_to):
    """Create a link between agents
    
    Args:
        set_holder (Agent | int | set[Agent | int]): The host (agent, id, or set) of the link
        link_name (str): The link name
        set_to (Agent | set[Agent]): The items to link to"""
def linked_to (link_source, link_name: str):
    """Get the set of ids that the source is linked to for the given key.
    
    Args:
        link_source (Agent | int): The agent or id to check
        link_name (str): The key/name of the inventory item
    Returns:
        set[int]: The set of linked ids"""
def set_dedicated_link (so, link_name: str, to):
    """Set the agent linked to
    
    !!! Note
        Dedicated link means there is only one thing linked to 1-1
    
    Args:
        link_name (str): The link name
        to (Agent | int): The single agent or id or None"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_id_list (the_set):
    """Converts a set to a list of ids
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[int]: A list of agent ids"""
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
def unlink (set_holder, link_name: str, set_to):
    """Removes the link between things
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or set of agents (ids or objects)
        link_name (str): Link name
        set_to (Agent | int | set[Agent | int]): The agent or set of agents (ids or objects) to add a link to"""
