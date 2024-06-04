from sbs_utils.agent import Agent
def get_dedicated_link (so, link):
    """Get the agent linked to
    
    !!! Note
        Dedicated link means there is only one thing linked to 1-1
    
    Args:
        link (str): The link name
    
    Returns:
        agent: The single agent or None"""
def has_link (key: str):
    """get the object that have a link item with the given key
    
    Args:
        key (str): The key/name of the inventory item
    
    Returns:
        set: set of ids"""
def has_link_to (link_source, link_name: str, link_target):
    """check if target and source are linked to for the given key
    
    Args:
        link_source (agent): The agent hosting the link
        link_name (str): The key/name of the inventory item
    
    Returns:
        set | None: set of ids"""
def link (set_holder, link, set_to):
    """create a link between agents
    
    Args:
        set_holder (agent | agent set): The host (set) of the link
        link (str): The link name
        set_to (agent|agent set): The items to link to"""
def linked_to (link_source, link_name: str):
    """get the set that inventor the source is linked to for the given key
    
    Args:
        link_source(id): The id object to check
        link_name (str): The key/name of the inventory item
        set | None: set of ids"""
def set_dedicated_link (so, link, to):
    """Set the agent linked to
    
    !!! Note
        Dedicated link means there is only one thing linked to 1-1
    
    Args:
        link (str): The link name
        to (agent): The single agent or None"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def to_id_list (the_set):
    """converts a set to a list of ids
    
    Args:
        the_set (set|list): a set of agents or ids
    
    Returns:
        list: of agent ids"""
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
def unlink (set_holder, link, set_to):
    """removes the link between things
    
    Args:
        set_holder (agent|agent set): An agent or set of agents (ids or objects)
        link (str): Link name
        set_to (agent|agent set): The agents(s) to add a link to"""
