from sbs_utils.helpers import FrameContext
def _back_tab_for (client_id, tab_name):
    """Substitute the crew console for whatever a boarded console was asked for, and a
    mission's Back override (gui_tab_back_override) for everything else."""
def _boarded_back_tab (client_id):
    """Which substitution applies to THIS console, or None if it is not boarded.
    
    A suit first: a console flying one is out in a relic, where the grid crew console has
    nothing to draw. Asked in that order rather than by CONSOLE_TYPE because the suit is
    the thing the client is actually assigned to."""
def _tab_client_id ():
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
    
    Falls back to the event when there is no page (server-side setup code, tests)."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def gui_app_activate (app_name: str):
    """Records which ePADD app this client is on. Injected by every `//gui/app` label.
    
    DELIBERATELY DOES NOT TOUCH `__active_tab__`. That asymmetry with
    `gui_tab_activate` is the whole return-point mechanism: an app never overwrites the
    tab you were on, so the PADD's single Back knows where to send you with nothing
    having to capture it.
    
    Args:
        app_name (str): The path of a //gui/app"""
def gui_app_get_active (client_id=None):
    """The ePADD app this client is on, or "" when they are not in the PADD.
    
    Takes an explicit client because the PAGE asks this question while drawing, and
    `_tab_client_id` answers with the ambient page - which during a strip build is not
    reliably the page being built. The same distinction `epadd._client_id` documents."""
def gui_tab_activate (tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    This is general called automatically by //gui/tab and //console labels
    
    ALSO ENDS THE PADD. Arriving at a tab is how you leave the ePADD, so this clears
    `__active_app__` - otherwise the strip would go on drawing the PADD's bar over a
    console. Doing it here rather than in each tab means nothing has to remember to.
    
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
    
    A console that is currently BOARDED goes back to the crew console instead, whatever
    the caller asked for - see the comment above. Nothing to do at the call sites.
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_back_override (client_id, tab_name):
    """Send this console's Back to `tab_name`, whatever a screen asks for.
    
    For a console that is somewhere other than the console it picked - a pilot in the
    cockpit picked the Hangar, so every ePADD screen's `gui_tab_back(CONSOLE_SELECT)`
    said "hangar", and Back pulled them out of their craft mid-flight. The mission sets
    this when the pilot takes the seat and clears it when they leave; no call site
    changes. A boarded or EVA console's own swap still wins."""
def gui_tab_back_override_clear (client_id):
    """Forget a Back target set by gui_tab_back_override."""
def gui_tab_back_while_boarded (tab_name=None, kind='grid'):
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
        str | None: the name now installed for that kind."""
def gui_tab_boarded_back_clear ():
    """Drop every substitution (called by `reset_mission_state`).
    
    A LATCH, not a container: an addon installs it at its top level, so one left behind
    would point the next mission's Back at a tab whose route no longer exists."""
def gui_tab_boarded_back_tab (kind='grid'):
    """The tab a boarded console's Back goes to, or None when nothing installed one."""
def gui_tab_boarded_back_tabs ():
    """Every installed substitution, as ``{kind: tab}``. For tools and the reset ledger."""
def gui_tab_clear_top ():
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_enable (tab_name: str):
    """Enable a tab on the console tabs
    
    A NAME THAT IS NOT A STRING IS IGNORED, not a crash. Callers pass a variable -
    `gui_tab_back(CONSOLE_SELECT)` is the shipped shape - and a task variable that was
    never set arrives as None, which used to reach `None.split(",")` and raise INSIDE a
    GUI build. A screen that cannot draw is a far worse outcome than a screen with no
    back tab, and the missing tab is reported where it is noticed rather than here.
    
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
