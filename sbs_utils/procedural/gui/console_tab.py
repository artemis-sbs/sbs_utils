from ..query import to_id
from ..inventory import get_inventory_value, set_inventory_value
from ...helpers import FrameContext


def gui_tab_enable(tab_name):
    client_id = FrameContext.client_id

    tabs = get_inventory_value(client_id, "console_tabs", {})
    tab_names = tab_name.split(",")
    for tab_name in tab_names:
        tab_name = tab_name.strip().lower()
        tabs[tab_name] = True
    set_inventory_value(client_id, "console_tabs", tabs)
    
def gui_tab_back(tab_name):
    client_id = FrameContext.client_id
    gui_tab_enable(tab_name)
    set_inventory_value(client_id, "__back_tab__", tab_name)

def gui_tab_add_top(tab_name):
    client_id = FrameContext.client_id

    tabs = get_inventory_value(client_id, "top_tabs", {})
    tab_names = tab_name.split(",")
    for tab_name in tab_names:
        tab_name = tab_name.strip().lower()
        tabs[tab_name] = True
    set_inventory_value(client_id, "top_tabs", tabs)

def gui_tab_enable_top():
    client_id = FrameContext.client_id

    tabs = get_inventory_value(client_id, "top_tabs", {})
    if len(tabs.keys())>0:
        top_tabs = ",".join(tabs.keys())
        gui_tab_enable(top_tabs)

# def gui_add_console_tab(id_or_obj, console, tab_name, label):
#     """adds a tab definition 

#     Args:
#         id_or_obj (agent): agent id or object
#         console (str): Console name
#         tab_name (str): Tab name
#         label (label): Label to run when tab selected
#     """    
#     ship_id = to_id(id_or_obj)
#     console = console.lower()
#     tabs = get_inventory_value(ship_id, "console_tabs", {})
#     console_tabs = tabs.get(console, {})
#     console_tabs[tab_name] = label
#     tabs[console] = console_tabs
#     # set just in case this is the first time
#     set_inventory_value(ship_id, "console_tabs", tabs)


# def gui_remove_console_tab(id_or_obj, console, tab_name):
#     """removes a tab definition 

#     Args:
#         id_or_obj (agent): agent id or object
#         console (str): Console name
#         tab_name (str): Tab name
#     """        
#     ship_id = to_id(id_or_obj)
#     tabs = get_inventory_value(ship_id, "console_tabs", None)
#     if tabs is None: return
#     console_tabs = tabs.get(console, None)
#     if console_tabs is None: return
#     console_tabs.pop(tab_name)
#     if len(console_tabs) == 0:
#         tabs.pop(console)
#     #set_inventory_value(ship_id, "console_tabs", tabs)
