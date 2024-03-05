from ..agent import Agent
from .query import to_object_list, to_set, to_object, to_id_list, to_id

def has_link(key: str):
    """ get the object that have a link item with the given key

        Args:
            key (str): The key/name of the inventory item
        
        Returns:
            set: set of ids
        """
    return Agent.has_links_set(key)



def linked_to(link_source, link_name: str):
    """ get the set that inventor the source is linked to for the given key

    Args:
        link_source(id): The id object to check
        link_name (str): The key/name of the inventory item
        set | None: set of ids
    """
    link_source = Agent.resolve_py_object(link_source)
    return link_source.get_link_set(link_name)

def has_link_to(link_source, link_name: str, link_target):
    """check if target and source are linked to for the given key

    Args:
        link_source (agent): The agent hosting the link
        link_name (str): The key/name of the inventory item
    
    Returns:
        set | None: set of ids
    """
    link_source = Agent.resolve_py_object(link_source)
    return  link_source.has_link_to(link_name,link_target)

def link(set_holder, link, set_to):
    """create a link between agents

    Args:
        set_holder (agent | agent set): The host (set) of the link
        link (str): The link name
        set_to (agent|agent set): The items to link to
    """    
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            so.add_link(link, target)



def get_dedicated_link(so, link):
    """ Get the agent linked to

    !!! Note
        Dedicated link means there is only one thing linked to 1-1

    Args:
        link (str): The link name

    Returns:
        agent: The single agent or None
    """    
    # Dedicated links are one-to-one, 
    so = to_object(so)
    if so is None:
        return None
    return so.get_dedicated_link(link)
            
def set_dedicated_link(so, link, to):
    """ Set the agent linked to

    !!! Note
        Dedicated link means there is only one thing linked to 1-1

    Args:
        link (str): The link name
        to (agent): The single agent or None
    """    
    so = to_object(so)
    to = to_id(to)
    if so is None or to is None:
        return
    so.set_dedicated_link(link, to)


def unlink(set_holder, link, set_to):
    """removes the link between things

    Args:
        set_holder (agent|agent set): An agent or set of agents (ids or objects)
        link (str): Link name
        set_to (agent|agent set): The agents(s) to add a link to
    """    
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            if so is not None and target is not None:
                so.remove_link(link, target)
