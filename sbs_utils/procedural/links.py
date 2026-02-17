from ..agent import Agent
from .query import to_object_list, to_set, to_object, to_id_list, to_id

# TODO: Consider renaming this function? The name implies that it returns a boolean, which can easily trip people up if they are looking for a `get_links()` or similar.
def has_link(link_name: str):
    """
    Get the objects that have a link item with the given key.

    Args:
        link_name (str): The key/name of the link
    
    Returns:
        set[int]: set of ids
    """
    return Agent.has_links_set(link_name)



def linked_to(link_source, link_name: str):
    """
    Get the set of ids that the source is linked to for the given key.

    Args:
        link_source (Agent | int): The agent or id to check
        link_name (str): The key/name of the inventory item
    Returns:
        set[int]: The set of linked ids
    """
    link_source = Agent.resolve_py_object(link_source)
    if link_source is None:
        return set()
    return link_source.get_link_set(link_name)

def has_link_to(link_source, link_name: str, link_target) -> bool:
    """
    Check if target and source are linked to for the given key

    Args:
        link_source (Agent | int): The agent or id hosting the link
        link_name (str): The key/name of the inventory item
    
    Returns:
        bool: Does the link exist
    """
    link_source = Agent.resolve_py_object(link_source)
    if link_source is None:
        return False
    return  link_source.has_link_to(link_name,link_target)

def link(set_holder, link_name: str, set_to):
    """
    Create a link between agents

    Args:
        set_holder (Agent | int | set[Agent | int]): The host (agent, id, or set) of the link
        link_name (str): The link name
        set_to (Agent | set[Agent]): The items to link to
    """    
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            so.add_link(link_name, target)



def get_dedicated_link(so, link_name: str):
    """ 
    Get the agent linked to the specified agent.

    !!! Note
        Dedicated link means there is only one thing linked to 1-1

    Args:
        link_name (str): The link name

    Returns:
        int | None: The id of a single agent or None
    """    
    # Dedicated links are one-to-one, 
    so = to_object(so)
    if so is None:
        return None
    return so.get_dedicated_link(link_name)
            
def set_dedicated_link(so, link_name: str, to):
    """ 
    Set the agent linked to

    !!! Note
        Dedicated link means there is only one thing linked to 1-1

    Args:
        link_name (str): The link name
        to (Agent | int): The single agent or id or None
    """    
    so = to_object(so)
    to = to_id(to)
    if so is None or to is None:
        return
    so.set_dedicated_link(link_name, to)


def unlink(set_holder, link_name: str, set_to):
    """
    Removes the link between things

    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or set of agents (ids or objects)
        link_name (str): Link name
        set_to (Agent | int | set[Agent | int]): The agent or set of agents (ids or objects) to add a link to
    """    
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            if so is not None and target is not None:
                so.remove_link(link_name, target)
