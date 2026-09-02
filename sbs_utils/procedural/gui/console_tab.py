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



def _tab_client_id():
    """Whose tab strip is being declared: the PAGE's client, not the event's.

    These declarations are read back by `MastStoryPage` off `self.client_id` - the
    page's own client - and were written here off `FrameContext.client_id`, which is
    the current EVENT's client. Those are the same on a click, a keypress or a plain
    repaint, and they are NOT the same when a page rebuilds because something else
    emitted a signal.

    A build finishing is exactly that case: `beacon_build_done` runs on the SERVER,
    emits `item_changed`, and the console's `on signal` handler repaints. `tick_in_context`
    corrects FrameContext.page and .task to the console's - but not the event - so every
    gui_tab_* call in that repaint declared tabs for client 0 while the page drew its
    strip from the console's own (now empty, because drawing CONSUMES them). The strip
    came back the next time the player touched anything, because a click carries the
    right client id. Reported as "the top tabs disappear the moment the build completes,
    and come back when you select something".

    Falls back to the event when there is no page (server-side setup code, tests).
    """
    page = FrameContext.page
    cid = getattr(page, "client_id", None) if page is not None else None
    return FrameContext.client_id if cid is None else cid


def gui_tab_get_list():
    from ...mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
    return list (GuiTabDecoratorLabel.all.keys())


def gui_tab_enable(tab_name: str):
    """Enable a tab on the console tabs

    A NAME THAT IS NOT A STRING IS IGNORED, not a crash. Callers pass a variable -
    `gui_tab_back(CONSOLE_SELECT)` is the shipped shape - and a task variable that was
    never set arrives as None, which used to reach `None.split(",")` and raise INSIDE a
    GUI build. A screen that cannot draw is a far worse outcome than a screen with no
    back tab, and the missing tab is reported where it is noticed rather than here.

    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons
    """
    client_id = _tab_client_id()

    if not isinstance(tab_name, str) or not tab_name.strip():
        return

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
    client_id = _tab_client_id()
    if not isinstance(tab_name, str) or not tab_name.strip():
        return                      # see gui_tab_enable: an unset variable, not a crash
    gui_tab_enable(tab_name)
    set_inventory_value(client_id, "__back_tab__", tab_name)

def gui_tab_activate(tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    This is general called automatically by //gui/tab and //console labels

    ALSO ENDS THE PADD. Arriving at a tab is how you leave the ePADD, so this clears
    `__active_app__` - otherwise the strip would go on drawing the PADD's bar over a
    console. Doing it here rather than in each tab means nothing has to remember to.

    Args:
        tab_name (str): The path of a //gui/tab
    """
    client_id = _tab_client_id()
    set_inventory_value(client_id, "__active_tab__", tab_name)
    set_inventory_value(client_id, "__active_app__", None)

def gui_tab_get_active():
    """returns the active tab

    Args:
        tab_name (str): The path of a //gui/tab
    """
    client_id = _tab_client_id()
    return get_inventory_value(client_id, "__active_tab__", "")


def gui_app_activate(app_name: str):
    """Records which ePADD app this client is on. Injected by every `//gui/app` label.

    DELIBERATELY DOES NOT TOUCH `__active_tab__`. That asymmetry with
    `gui_tab_activate` is the whole return-point mechanism: an app never overwrites the
    tab you were on, so the PADD's single Back knows where to send you with nothing
    having to capture it.

    Args:
        app_name (str): The path of a //gui/app
    """
    client_id = _tab_client_id()
    set_inventory_value(client_id, "__active_app__", app_name)


def gui_app_get_active(client_id=None):
    """The ePADD app this client is on, or "" when they are not in the PADD.

    Takes an explicit client because the PAGE asks this question while drawing, and
    `_tab_client_id` answers with the ambient page - which during a strip build is not
    reliably the page being built. The same distinction `epadd._client_id` documents.
    """
    if client_id is None:
        client_id = _tab_client_id()
    return get_inventory_value(client_id, "__active_app__", "") or ""


def gui_tab_add_top(tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons
    """
    client_id = _tab_client_id()

    tabs = get_inventory_value(client_id, "top_tabs", {})
    tab_names = tab_name.split(",")
    for tab_name in tab_names:
        tab_name = tab_name.strip().lower()
        tabs[tab_name] = True
    set_inventory_value(client_id, "top_tabs", tabs)


def gui_tab_is_top(tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons
    """
    client_id = _tab_client_id()

    tabs = get_inventory_value(client_id, "top_tabs", {})
    tab_names = tab_name.split(",")
    for tab_name in tab_names:
        tab_name = tab_name.strip().lower()
        if not tabs.get(tab_name):
            return False
    return True


def gui_tab_remove_top(tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons
    """
    client_id = _tab_client_id()

    tabs = get_inventory_value(client_id, "top_tabs", {})
    tab_names = tab_name.split(",")
    for tab_name in tab_names:
        tab_name = tab_name.strip().lower()
        tabs.pop(tab_name, False)
    set_inventory_value(client_id, "top_tabs", tabs)

def gui_tab_clear_top():
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons
    """
    client_id = _tab_client_id()
    set_inventory_value(client_id, "top_tabs", {})


def gui_tab_enable_top():
    client_id = _tab_client_id()

    tabs = get_inventory_value(client_id, "top_tabs", {})
    if len(tabs.keys())>0:
        top_tabs = ",".join(tabs.keys())
        gui_tab_enable(top_tabs)

