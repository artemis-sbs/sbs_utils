from ..query import to_id
from ..inventory import get_inventory_value, set_inventory_value


def gui_add_console_tab(id_or_obj, console, tab_name, label):
    """adds a tab definition 

    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected
    """    
    ship_id = to_id(id_or_obj)
    console = console.lower()
    tabs = get_inventory_value(ship_id, "console_tabs", {})
    console_tabs = tabs.get(console, {})
    console_tabs[tab_name] = label
    tabs[console] = console_tabs
    # set just in case this is the first time
    set_inventory_value(ship_id, "console_tabs", tabs)


def gui_remove_console_tab(id_or_obj, console, tab_name):
    """removes a tab definition 

    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
    """        
    ship_id = to_id(id_or_obj)
    tabs = get_inventory_value(ship_id, "console_tabs", None)
    if tabs is None: return
    console_tabs = tabs.get(console, None)
    if console_tabs is None: return
    console_tabs.pop(tab_name)
    if len(console_tabs) == 0:
        tabs.pop(console)
    #set_inventory_value(ship_id, "console_tabs", tabs)
