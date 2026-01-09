"""
Console tabs:

The console tab system allows for creating a page tabbing system that allows the user to
switch between pages quickly.

Tabs are defined with a //gui/tab label.
This label defines what happens when that tab is press.

Example:

    # Allow the debug tab to be shown
    # at the top level
    gui_tab_add_top("debug")

    //gui/tab/debug
        jump show_debug_page

    //gui/tab/brain
        jump show_brain_page

    === show_debug_page
        # Set the return page
        gui_tab_back(CONSOLE_SELECT)
        # Add the brain as a tab of the debug page
        gui_tab_enable("brain")
        # Set the back button to the last selected standard console
        # Rest of code to show page

    === show_brain_page
        # Set the back button to the last selected standard console
        gui_tab_back("debug")
        # Rest of code to show page



"""
from ..query import to_id
from ..inventory import get_inventory_value, set_inventory_value
from ...helpers import FrameContext


def gui_tab_enable(tab_name: str):
    """Enable a tab on the console tabs

    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons
    """
    client_id = FrameContext.client_id

    tabs = get_inventory_value(client_id, "console_tabs", {})
    tab_names = tab_name.split(",")
    for tab_name in tab_names:
        tab_name = tab_name.strip().lower()
        tabs[tab_name] = True
    set_inventory_value(client_id, "console_tabs", tabs)
    
def gui_tab_back(tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    The back tag is set by //gui/tab and //console labels
    This allows overriding

    Args:
        tab_name (str): The path of a //gui/tab
    """
    client_id = FrameContext.client_id
    gui_tab_enable(tab_name)
    set_inventory_value(client_id, "__back_tab__", tab_name)

def gui_tab_activate(tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    This is general called automatically by //gui/tab and //console labels

    Args:
        tab_name (str): The path of a //gui/tab
    """
    client_id = FrameContext.client_id
    set_inventory_value(client_id, "__active_tab__", tab_name)

def gui_tab_get_active():
    """returns the active tab

    Args:
        tab_name (str): The path of a //gui/tab
    """
    client_id = FrameContext.client_id
    get_inventory_value(client_id, "__active_tab__", "")


def gui_tab_add_top(tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons
    """
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

