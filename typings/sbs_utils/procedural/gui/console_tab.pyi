from sbs_utils.helpers import FrameContext
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
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
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
