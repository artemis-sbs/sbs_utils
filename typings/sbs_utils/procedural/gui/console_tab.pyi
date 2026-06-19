from sbs_utils.helpers import FrameContext
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def gui_tab_activate (tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    This is general called automatically by //gui/tab and //console labels
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_add_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_back (tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    The back tag is set by //gui/tab and //console labels
    This allows overriding
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_clear_top ():
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_enable (tab_name: str):
    """Enable a tab on the console tabs
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_enable_top ():
    ...
def gui_tab_get_active ():
    """returns the active tab
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_get_list ():
    ...
def gui_tab_is_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_remove_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
