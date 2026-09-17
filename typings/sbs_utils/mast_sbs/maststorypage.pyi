from sbs_utils.agent import Agent
from sbs_utils.pages.layout.blank import Blank
from sbs_utils.pages.layout.dropdown import Dropdown
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.pages.layout.icon import Icon
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.maststory import MastStory
from sbs_utils.pages.layout.row import Row
from sbs_utils.mast_sbs.maststoryscheduler import StoryScheduler
from sbs_utils.pages.layout.text import Text
def _console_identity (client_id, page_console):
    """Which console this client is on, for app scoping and the badge.
    
    What THIS BUILD declared wins, and the door's record fills in only when the build
    declared nothing. Both orders agree in the ordinary case; they part on a build that
    activates one console while the client's sticky CONSOLE_TYPE still names another,
    and there the screen being drawn is the honest answer.
    
    The fallback is the point, though. `gui_console_enter` - the one door - writes
    CONSOLE_TYPE and never touches `page.console`, so a console entered through it and
    nothing else reports `page.console == ""` for the rest of its life. The away screen
    is the shipped example (`gui_console_enter(cid, "crew")`, no `@console/crew`
    label), and reading the page alone answered "" for it - which left the crew console
    scoped as if it were no console at all. The same mis-read cost three rounds on the
    messages app (2026-09-01), where it made `message_select` drop every pick in
    silence.
    
    NOT a test for "is this a console screen" - CONSOLE_TYPE is sticky, and nothing
    clears it when a client leaves one. See `_epadd_belongs_here`."""
def _identity_icon_props (accent):
    """The glyph's props, or None when nothing answers to that name.
    
    A missing icon draws nothing rather than some arbitrary index - a wrong glyph is
    worse than no glyph, because it looks deliberate."""
def _identity_right (client_id):
    """Where the badge ends, and therefore where the tab row begins."""
def _identity_style (text, accent):
    """The badge's style string, in one place because two callers build it.
    
    ESCAPED, not hand-quoted: a crew member's name is authored content and a `;` or a
    backtick in it would otherwise end the style string early and draw the rest of it
    as text. `tests/test_gui_text_quoting` enforces this across the library.
    
    NOT CENTRED. The region is a percentage of the screen, so on a wide display it is
    a wide box - and a centred label in a wide box floats away from the glyph beside it,
    which is the growing gap the playtest caught on a larger screen. Left is the default
    and the column is content-sized, so the name sits against the glyph at any size."""
def _is_main_screen (client_id, console):
    """Whether this console is the shared view rather than one person's station.
    
    The badge names the person at the console, and the main screen is the whole
    room's - a name on it is either wrong or somebody else's. The same test the away
    team already uses to decide the main screen takes no character."""
def _pct_x (client_id, px, fallback):
    """A horizontal pixel measurement as the PERCENT a Layout's bounds want."""
def _strip_area (left_px, right='100'):
    """`area:` for a strip-height band starting at `left_px`."""
def _strip_bottom (client_id):
    """How far down the strip reaches, as the PERCENT a Layout's bounds want.
    
    A Layout's rect is a percentage while the row inside it is declared in PIXELS, so
    the two only agree at one resolution. They did not agree at the playtest's: the
    region was 3% (~32px at 1080) against a 35px row, so the press highlight stopped
    above the bottom of the bar and the badge read as floating in it.
    
    Converted per client, because that is what the percentage has to track."""
def _strip_left (client_id):
    """Where the strip starts: just past the engine's Options button."""
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def compose_handler (existing, layout_item, runtime_node):
    """Return the `(layout_item, node)` tuple a tag_map key should now hold.
    
    Replaces, exactly as before, unless there is a real handler already
    registered for this same widget -- then the two are chained."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_mission_name ():
    """Get the name of the current mission.
    
    Returns the name derived from the script directory basename.
    Cached after first call.
    
    Returns:
        str: The mission folder name."""
def get_startup_mission_name ():
    """Get the default mission name from preferences.
    
    Returns:
        str: The default mission folder name from game preferences."""
def gui_reroute_client (client_id, label, data=None):
    """Jump a specific client's GUI task to a new label immediately.
    
    Finds the client's active page, optionally sets variables from ``data``,
    then jumps the page's GUI task to ``label`` and ticks it in the current
    frame context.
    
    Args:
        client_id (int): The client to reroute.
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.
    
    Example:
        gui_reroute_client(CLIENT_ID, briefing_screen)"""
def gui_text_escape (s):
    """Quote a dynamic value for safe inclusion as a ``$text:`` style value.
    
    Wraps ``s`` in backticks so any ``:`` or ``;`` it contains is treated as
    literal text by the style parser rather than a style property (issue #569).
    A literal backtick -- the quoting delimiter itself -- is stripped. An empty
    or ``None`` value returns ``""`` so the caller emits ``$text:;`` with no
    stray backtick in the box (issue #641).
    
    Use this ONLY on the dynamic value, e.g. ``f"$text:{gui_text_escape(name)};color:red;"``
    -- never on a whole authored props string, so the author's own ``:``/``;``
    styling is left untouched."""
def has_inventory_value (key: str, value):
    """Return the set of agent IDs whose inventory value for ``key`` equals ``value``.
    
    Args:
        key (str): The inventory key to look for.
        value: The exact value to match.
    
    Returns:
        set[int]: IDs of agents whose ``key`` inventory entry equals ``value``."""
def is_dev_build ():
    """Check if the current mission is a development build.
    
    Returns True if a .git directory exists in the mission folder.
    
    Returns:
        bool: True if running in development mode, False otherwise."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
class StoryPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _epadd_belongs_here (self, console, enabled_tabs):
        """Whether THIS build is a console screen the PADD belongs on.
        
        The PADD's shell route existing says the MISSION has one, not that this
        particular screen is a console. Without this test the button replaced the strip
        on every build that queued one - so it turned up on the start screen, on console
        select and on the game-results screen, and on the main screen, which is what the
        playtest reported (2026-09-01).
        
        Three signals, and none works alone:
        
        * **Being in the PADD** ends the question. An app screen declares no console and,
          since apps stopped calling `gui_tab_back`, no tabs either - so without this the
          status region would vanish the moment you opened an app, which is the one place
          it is most wanted.
        * `self.console` is PER BUILD - `pending_console` is reset after every swap - so
          it means "this screen activated a console", not "this client was ever on one".
          `gui_console()` sets it; console select, the results screen and the start
          screen never call it. But a MORPHED console does not call it either.
        * `enabled_tabs` is also per build, because drawing CONSUMES it. A morphed
          console declares its back tab and so has one; the three screens above declare
          nothing.
        
        CONSOLE_TYPE is deliberately not the test. It is sticky - nothing clears it when
        a client leaves a console - so the results screen still reports whatever station
        the player last sat at, and console select sets it outright."""
    def _forget_parked_widgets (client_id=None):
        """Drop the parking record - a client going away, a mission reset, a test."""
    def _grid_note_cell (self):
        """Count one grid cell, and break the row after every N.
        
        Only at the grid's OWN depth: anything a cell builds inside itself belongs to
        that cell, not to the grid."""
    def _grid_style_row (self):
        """Apply the grid's row style to the row it just started. A grid creates its
        own rows, so this is the only way an author can size them - and a row that
        declares nothing is 1fr, which stretches a short grid over the whole section."""
    def _log_page_death (self, client_id):
        """Name the console and the last thing its GUI task was standing on.
        
        Called only from the non-dev branch that pops a page whose tasks have all
        finished. The screen going dark is the symptom a scripter reports; this
        is the one line that says which console and which label, so the report
        arrives with something to look at."""
    def _queue_identity_region (self, console, epadd_label):
        """The PADD: the strip's left two slots, as ONE click target.
        
        It used to be a band of its own with an absolute pixel rect UNDER the strip,
        which put it over the ship-data panel and collided with its readouts (playtest,
        2026-09-01). It belongs on the strip, where every other control on that bar is.
        
        A REGION, NOT TWO COLUMNS. Built as its own `Layout` rather than as two columns
        of the tab row, because a Row gives each column its own click region - so a
        glyph and a name sitting side by side were two hit targets that did the same
        thing, and pressing either highlighted only its own half. One Layout emits one
        region over its whole bounds, which is what makes the status read as a single
        control.
        
        NO WORD FOR IT. The glyph is the engine's own `phone`, from the same
        grid-icon-sheet the engineering grid draws from, so the label is free to say who
        is sitting there instead of naming the button."""
    def _retire_dropped_engine_widgets (prev, current, client_id, my_sbs):
        """Push offscreen any engine widget this console no longer declares -
        but ONLY the ones we know how to put back.
        
        An engine widget cannot be un-declared. The console's widget list is what
        the engine draws from, and it keeps what it was given, so sending a
        SHORTER list does not retire the ones that fell off - they carry on
        rendering at whatever rect they last had, against whatever object the
        console was last pointed at. When that object has been deleted, the
        engine walks freed memory: that is how a client died in
        ViewGridObjectListDraw two minutes after the mission ended, still drawing
        the Engineering grid list for a ship that no longer existed.
        
        Pushing the rect offscreen is the one thing that does work on a widget
        already shown - the same trick gui_widget_offscreen documents, applied
        automatically here so every console inherits it rather than each screen
        having to remember. Only runs when the list actually changes, which is
        rare (a console switch, or a jump to the results screen).
        
        WE CAN ONLY TAKE AWAY WHAT WE CAN GIVE BACK. Parking is permanent -
        re-declaring a widget in the list does not restore the rect it was pushed
        to - so a widget that comes back has to be sent a rect, and the only rect
        we can honestly send is one a script placed it at (``Gui.widget_rects``).
        A widget the ENGINE laid out has no such record, and guessing one wrecks
        the console: this used to un-park everything to the FULL CONSOLE, so
        clicking the Upgrades tab on Weapons and clicking back left all six
        engine-laid controls stacked over the whole screen. Helm and Weapons are
        the only LegendaryMissions consoles that leave anything to the engine,
        which is exactly where it was reported.
        
        So a widget with no placement record is left entirely alone - never
        parked, and therefore never stuck offscreen either. That is also what
        keeps the main screen's 3dview working: nothing places it, so the
        Tactical toggle can neither park nor lose it."""
    def _tick_identity_badge (self):
        """Keep the badge current while the console sits in `await gui()`.
        
        A SIGNAL DOES NOT WAKE `await gui()`, and a console parked on Helm all game
        never rebuilds - so without this the count is frozen at whatever it said when
        the screen was built, which is precisely the case the badge exists for.
        
        Updates the widget rather than the page: the dirty system re-renders a changed
        widget on its own, so nothing here repaints a screen."""
    def activate_console (self, console):
        ...
    def add_alias (self, layout_item, runtime_node=None):
        """Register an author's `tag:` name so gui_update() can resolve it.
        
        An extra key in the SAME tag_map, exactly as click_tag has always earned a
        second entry -- so every consumer that resolves by tag_map (gui_update,
        message routing, the log panel's liveness check) picks it up with no further
        change. The engine keeps the library-managed tag (LM #349).
        
        Called from add_tag for widgets, and directly from gui_row/gui_section, which
        never reach add_tag -- which is why a named ROW was unreachable before."""
    def add_console_widget (self, widget):
        ...
    def add_content (self, layout_item, runtime_node):
        ...
    def add_on_click (self, runtime_node):
        ...
    def add_row (self):
        ...
    def add_section (self, tag=None):
        ...
    def add_tag (self, layout_item, runtime_node):
        ...
    def advance_tag_generation (self):
        """Move the widget-tag counters on to the next GUI build.
        
        The +2000 gap is what keeps a new build's tags clear of the build still
        on screen; only the previous build is ever live, so the numbers may
        safely wrap once they get large.
        
        The modulo used to be written `self.rebuild_tag + 100 % 100000`, which
        Python binds as `+ (100 % 100000)` == `+ 100` -- so the wrap never
        happened and the tags grew without bound. Measured against the engine, a
        GUI redrawn ten times was already handing it tags near 20,000."""
    def get_path (self):
        ...
    def get_pending_layout (self):
        ...
    def get_pending_row (self):
        ...
    def get_tag (self):
        ...
    def grid_begin (self, columns, row_style=None):
        """Enter a gui_grid() context: subsequent add_content()s flow into an
        ``columns``-wide grid, auto-breaking rows. Nestable."""
    def grid_end (self):
        """Leave the current gui_grid() context, padding the final row with Hole
        spacers so its columns stay aligned, then start a fresh row."""
    def gui_queue_console_tabs (self):
        ...
    def on_begin_presenting (self):
        ...
    def on_end_presenting (self):
        ...
    def on_event (self, event):
        """on_event
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def on_message (self, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def on_new_gui (self):
        ...
    def pop_sub_section (self, add_content, is_rebuild):
        ...
    def present (self, event):
        """Present the gui """
    def push_sub_section (self, style, layout_item, is_rebuild):
        ...
    def set_button_layout (self, layout, gui_promise):
        ...
    def set_widget_list (self, console, widgets):
        ...
    def start_story (self, client_id):
        ...
    def swap_gui_promise (self, pending):
        ...
    def swap_layout (self):
        ...
    @property
    def task (self):
        ...
    def tick_gui_task (self):
        """tick_gui_task
        
        Called to have the page run any tasks they have prior to present"""
    def update_props_by_tag (self, tag, props, test):
        """Apply props to the widget registered under `tag`.
        
        Returns True when a widget was found and updated. A miss is not an error --
        the tag may name a listbox row that is currently scrolled out of view, and
        those are built only while visible -- but the caller can now tell, which it
        could not before."""
class TabControl(Text):
    """class TabControl"""
    def __init__ (self, tag, message, label, page) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
class TabOverflow(Dropdown):
    """The tabs that did not fit, as a menu. Selecting one jumps to it exactly as
    clicking its tab would - the same two lines TabControl runs."""
    def __init__ (self, tag, props, labels, page) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
