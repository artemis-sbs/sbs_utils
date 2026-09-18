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
    
# --- where Back goes for somebody who is not on their ship ----------------------------
#
# A boarded console's Back used to walk the crew member to Helm, with their character
# still standing on a planet. Fixing it at the CALL SITES means four `gui_tab_back` calls
# in LM's `consoles/epadd.mast` and ten more across the rest of it, and "the guard existed
# in the page and had been applied in one place only" is a mistake this codebase has
# already made and written down (`epadd.py:_console_identity`). So it is fixed HERE, at
# the one choke point that writes `__back_tab__`, the same argument `gui_tab_activate`
# makes for ending the PADD in one place: doing it here means nothing has to remember to.
#
# INSTALLED, NOT ASSUMED. The library cannot declare a `//gui/tab` - routes are MAST - so
# the substitution is armed by whichever addon owns the crew console, naming the tab it
# declared. Nothing installed means no substitution and the old behaviour, which matters:
# substituting unconditionally would send Back to a tab with no route behind it, and a
# dead Back is no better than one that goes to the wrong place.
#
# ONE ENTRY PER BODY MODEL, not one global. There are two crew consoles now - the grid
# one (a deck you walk) and the EVA one (a suit you fly) - and each is declared by its own
# addon file, both of which call this at their top level. While this was a single global
# the LAST file loaded simply won: adding `boarding/eva_console.mast` sent the ePADD's
# Back to the EVA console for every GRID boarder, in every mission that loads the boarding
# addon and has no relics in it at all. Keyed, it is order-independent, and a mission that
# loads only one of the two is unchanged.
BOARDED_KIND_GRID = "grid"
BOARDED_KIND_EVA = "eva"

_BOARDING_BACK_TABS = {}


def gui_tab_back_while_boarded(tab_name=None, kind=BOARDED_KIND_GRID):
    """Name the tab a BOARDED console's Back should go to, or clear it with ``None``.

    Called once by the addon that declares that tab::

        gui_tab_back_while_boarded("boarding_crew")
        gui_tab_back_while_boarded("eva_crew", kind="eva")

        //gui/tab/boarding_crew
            jump boarding_crew_console

    Args:
        tab_name (str, optional): the `//gui/tab` to substitute. ``None`` clears it.
        kind (str, optional): which kind of boarded console this tab is for - ``"grid"``
            (a deck, the default and what every existing caller means) or ``"eva"`` (a
            suit). A console flying a suit takes the ``eva`` tab; anything else boarded
            takes the ``grid`` one.

    Returns:
        str | None: the name now installed for that kind.
    """
    key = str(kind or BOARDED_KIND_GRID).strip().lower() or BOARDED_KIND_GRID
    name = tab_name.strip().lower() if isinstance(tab_name, str) and tab_name.strip() \
        else None
    if name is None:
        _BOARDING_BACK_TABS.pop(key, None)
    else:
        _BOARDING_BACK_TABS[key] = name
    return name


def gui_tab_boarded_back_tab(kind=BOARDED_KIND_GRID):
    """The tab a boarded console's Back goes to, or None when nothing installed one."""
    return _BOARDING_BACK_TABS.get(str(kind or BOARDED_KIND_GRID).strip().lower())


def gui_tab_boarded_back_tabs():
    """Every installed substitution, as ``{kind: tab}``. For tools and the reset ledger."""
    return dict(_BOARDING_BACK_TABS)


def gui_tab_boarded_back_clear():
    """Drop every substitution (called by `reset_mission_state`).

    A LATCH, not a container: an addon installs it at its top level, so one left behind
    would point the next mission's Back at a tab whose route no longer exists.
    """
    _BOARDING_BACK_TABS.clear()


def _boarded_back_tab(client_id):
    """Which substitution applies to THIS console, or None if it is not boarded.

    A suit first: a console flying one is out in a relic, where the grid crew console has
    nothing to draw. Asked in that order rather than by CONSOLE_TYPE because the suit is
    the thing the client is actually assigned to.
    """
    if not _BOARDING_BACK_TABS:
        return None
    eva = _BOARDING_BACK_TABS.get(BOARDED_KIND_EVA)
    if eva is not None:
        try:
            from ..eva import eva_my_suit
            if eva_my_suit(client_id) is not None:
                return eva
        except Exception:                   # noqa: BLE001 - a mission with no EVA
            pass
    grid = _BOARDING_BACK_TABS.get(BOARDED_KIND_GRID)
    if grid is None:
        return None
    try:
        from ..boarding import boarding_clients
    except Exception:                       # noqa: BLE001 - a mission with no boarding
        return None
    return grid if client_id in boarding_clients() else None


def _back_tab_for(client_id, tab_name):
    """Substitute the crew console for whatever a boarded console was asked for."""
    crew_tab = _boarded_back_tab(client_id)
    if crew_tab is None:
        return tab_name
    if tab_name.strip().lower() == crew_tab:
        return tab_name                     # already there; do not recurse into itself
    return crew_tab


def gui_tab_back(tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    The back tag is set by //gui/tab and //console labels
    This allows overriding

    A console that is currently BOARDED goes back to the crew console instead, whatever
    the caller asked for - see the comment above. Nothing to do at the call sites.

    Args:
        tab_name (str): The path of a //gui/tab
    """
    client_id = _tab_client_id()
    if not isinstance(tab_name, str) or not tab_name.strip():
        return                      # see gui_tab_enable: an unset variable, not a crash
    tab_name = _back_tab_for(client_id, tab_name)
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

