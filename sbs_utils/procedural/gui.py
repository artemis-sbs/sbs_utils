from .query import to_id
from .inventory import get_inventory_value, set_inventory_value


def gui_add_console_tab(id_or_obj, console, tab_name, label):
    ship_id = to_id(id_or_obj)
    console = console.lower()
    tabs = get_inventory_value(ship_id, "console_tabs", {})
    console_tabs = tabs.get(console, {})
    console_tabs[tab_name] = label
    tabs[console] = console_tabs
    #print(f"set {ship_id} {console} {tabs}")
    # set just in case this is the first time
    set_inventory_value(ship_id, "console_tabs", tabs)

def gui_remove_console_tab(id_or_obj, console, tab_name):
    ship_id = to_id(id_or_obj)
    tabs = get_inventory_value(ship_id, "console_tabs", None)
    if tabs is None: return
    console_tabs = tabs.get(console, None)
    if console_tabs is None: return
    console_tabs.pop(tab_name)
    if len(console_tabs) == 0:
        tabs.pop(console)
    #set_inventory_value(ship_id, "console_tabs", tabs)

