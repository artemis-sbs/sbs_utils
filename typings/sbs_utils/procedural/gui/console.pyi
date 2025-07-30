from sbs_utils.helpers import FrameContext
def all_roles (roles: str):
    """returns a set of all the agents with a given role.
    
    Args:
        roles (str): The roles comma separated
    
    Returns:
        agent id set: a set of agent IDs"""
def gui_activate_console (console):
    """set the console name for the client
    
    Args:
        console (str): The console name"""
def gui_console (console, is_jump=False):
    """Activates a console using the default set of widgets
    
    Args:
        console (str): The console name"""
def gui_console_clients (path, for_ships=None):
    """gets a set of IDs for matching consoles
    
    Args:
        console (str): The console name"""
def linked_to (link_source, link_name: str):
    """get the set that inventor the source is linked to for the given key
    
    Args:
        link_source(id): The id object to check
        link_name (str): The key/name of the inventory item
        set | None: set of ids"""
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a set of ids
    
    Args:
        the_set (set): set, list or single item
    
    Returns:
        set of things"""
