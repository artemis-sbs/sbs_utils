from sbs_utils.helpers import FrameContext
def all_roles (roles: str):
    """Returns a set of all the agents which have all of the given roles.
    
    Args:
        roles (str): A comma-separated list of roles.
    
    Returns:
        set[int]: a set of agent IDs."""
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
    """Get the set of ids that the source is linked to for the given key.
    
    Args:
        link_source (Agent | int): The agent or id to check
        link_name (str): The key/name of the inventory item
    Returns:
        set[int]: The set of linked ids"""
def role (role: str):
    """Returns a set of all the agents with a given role as a set of IDs.
    
    Args:
        role (str): The role.
    
    Returns:
        set[int]: a set of agent IDs."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a set of ids
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        set[Agent | CloseData | int]: A set containing whatever was passed in."""
