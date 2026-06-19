from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Promise
from sbs_utils.pages.widgets.tabbed_panel import TabbedPanel
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
def awaitable (func):
    ...
def delay_sim (seconds=0, minutes=0) -> sbs_utils.procedural.timers.Delay:
    """Suspend the current task for a duration measured in simulation time.
    
    Simulation time can be paused (e.g. when the game is paused).
    
    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
    
    Returns:
        Delay: A promise that resolves when the time has elapsed.
    
    Example:
        await delay_sim(seconds=5)
        "Five simulation seconds have passed.""""
def gui_blank (count=1, style=None):
    """Add one or more empty columns to the current layout row.
    
    Blanks occupy column space without rendering anything visible. Use them
    to push elements right, add padding, or center icons.
    
    Args:
        count (int, optional): Number of blank columns to insert. Defaults to
            1.
        style (str, optional): CSS-like style overrides applied to each blank.
            Defaults to None.
    
    Returns:
        Blank: The last blank layout item created.
    
    Example:
        gui_blank()
        gui_icon("icons/shield")
        gui_blank()"""
def gui_button (props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a button to the current GUI layout outside of an ``await gui()`` block.
    
    Unlike buttons declared with ``*`` or ``+`` inside ``await gui()``, this
    button is placed directly in the layout at the current position and fires
    its handler without ending the surrounding ``await gui()``. Use it for
    action buttons embedded in panels, listboxes, or info panels.
    
    Args:
        props (str): Button label text, optionally as a property string
            (e.g. ``"$text:Fire!;color:red;"``). Supports ``{var}``
            interpolation.
        style (str, optional): Additional CSS-like style overrides.
            End each property with a semicolon, e.g. ``"col-width:20%;"``.
            Defaults to None.
        data (object, optional): Arbitrary data passed to the handler.
            Available as ``__ITEM__`` and (if a dict) as individual variables.
            Defaults to None.
        on_press (label | callable | Promise, optional): What to do when the
            button is pressed. A label is jumped to; a callable is called; a
            Promise has its result set. Defaults to None.
        is_sub_task (bool, optional): When ``True`` the handler runs as an
            independent sub-task. Use ``False`` (default) only when pressing
            the button will rebuild the entire GUI via ``await gui()``.
            Defaults to False.
    
    Valid Styles:
        area:
            Format as `top, left, bottom, right`.
            Just numbers indicates percentage of the section or page to cover.
            Can also use `px` (pixels) or `em` (1em = height of text font).
            Can combine different units, e.g. `5+5px, 3em, 100-10em, 50px;` is a valid area.
        color:
            The color of the text
        background-color:
            The background color of the button
        padding:
            A gap inside the element (makes the button smaller, but the background still is there.)
        margin:
            The gap outside the element (makes the button smaller).
        col-width:
            The width of the button
        justify:
            Where the text is placed inside the button. `left`, `center`, or `right`
        font:
            The font to use. Overrides the font in prefernces.json
    
    
    
    Returns:
        layout object: The Layout object created"""
def gui_face (face, style=None):
    """Add a character face portrait to the current GUI layout.
    
    Renders the named face asset, typically used in comms panels to show the
    speaker's portrait.
    
    Args:
        face (str): Face asset name or property string, e.g. ``"crew/captain"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Face: The layout item created.
    
    Example:
        gui_face("crew/captain")"""
def gui_icon (props, style=None):
    """Add an icon image to the current GUI layout.
    
    Renders a non-interactive icon from the atlas or media path.
    
    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/torpedo"`` or ``"image:icons/torpedo;color:yellow;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Icon: The layout item created.
    
    Example:
        gui_icon("icons/shield")
        gui_text("{shield_pct}%")"""
def gui_info_panel (tab=0, tab_location=0, icon_size=0, var=None):
    """Create the standard info panel with a built-in ship-data tab.
    
    Initialises a ``TabbedPanel`` pre-loaded with a "hide" tab (icon 121) and
    a "ship_data" tab (icon 140). Additional tabs can be appended with
    ``gui_info_panel_add``. The panel object is stored in the GUI task under
    ``var`` so it can be retrieved and updated later.
    
    Args:
        tab (int, optional): Initially active tab index. Defaults to 0.
        tab_location (int, optional): Edge where tabs appear (0=left). Defaults to 0.
        icon_size (int, optional): Icon size in pixels. Defaults to 0 (auto).
        var (str, optional): Task variable name used to store the panel.
            Defaults to ``"__INFO_PANEL__"``.
    
    Returns:
        TabbedPanel: The info panel layout object.
    
    Example:
        tp = gui_info_panel()
        gui_info_panel_add("comms", 130, show_comms_tab)"""
def gui_info_panel_add (path, icon_index, show, hide=None, tick=None, var=None):
    """Add a tab to an existing info panel.
    
    If the panel is currently displayed, it is re-represented immediately.
    
    Args:
        path (str): Route name for this tab, used to switch to it programmatically.
        icon_index (int): Icon index displayed on the tab button.
        show (callable): ``show(cid, left, top, width, height)`` called when
            the tab becomes active.
        hide (callable, optional): Called when the tab is deactivated.
            Defaults to None.
        tick (callable, optional): Called each tick while the tab is active.
            Defaults to None.
        var (str, optional): Task variable holding the panel (set by
            ``gui_info_panel``). Defaults to ``"__INFO_PANEL__"``.
    
    Returns:
        TabbedPanel | None: The panel, or ``None`` if not found.
    
    Example:
        gui_info_panel_add("crew", 155, show_crew_tab, hide_crew_tab)"""
def gui_info_panel_remove (path, var=None):
    """Remove a tab from an info panel by its path name.
    
    If the panel is currently displayed and the tab was actually present,
    the panel is re-represented immediately.
    
    Args:
        path (str): Route name of the tab to remove (as passed to
            ``gui_info_panel_add``).
        var (str, optional): Task variable holding the panel. Defaults to
            ``"__INFO_PANEL__"``.
    
    Returns:
        TabbedPanel | None: The panel, or ``None`` if not found.
    
    Example:
        gui_info_panel_remove("crew")"""
def gui_info_panel_send_message (client_id, message=None, message_color=None, path=None, title=None, title_color=None, banner=None, banner_color=None, face=None, icon_index=None, icon_color=None, button=None, history=True, time=-1):
    """Send a message card to a client's info panel.
    
    The message is queued under the given ``path`` tab and displayed when that
    tab is active. If a ``button`` label is provided the call suspends until the
    player presses it. Messages are stored in history (up to 9 items) unless
    ``history=False``.
    
    Args:
        client_id (int | set): Client(s) to receive the message.
        message (str, optional): Main body text.
        message_color (str, optional): CSS color for the body text.
        path (str, optional): Tab path to place the message in. Defaults to
            ``"message"``.
        title (str, optional): Bold header line above the message.
        title_color (str, optional): CSS color for the title.
        banner (str, optional): Larger banner text shown above the title.
        banner_color (str, optional): CSS color for the banner.
        face (str, optional): Face/portrait key to display alongside the message.
        icon_index (int, optional): Icon index to display alongside the message.
        icon_color (str, optional): CSS color for the icon.
        button (str | list, optional): Button label(s) to show. When set the
            function returns an awaitable Promise that resolves on button press.
        history (bool, optional): Append to message history. Defaults to True.
        time (int, optional): Auto-dismiss after this many seconds if no button
            is configured. Defaults to -1 (use panel default of 10 s).
    
    Returns:
        Promise | None: Resolves when the button is pressed, or None if no
            button was specified.
    
    Example:
        await gui_info_panel_send_message(CLIENT_ID,
            title="New Orders",
            message="Report to DS1 immediately.",
            face="captain")"""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    """Add a listbox to the current GUI layout.
    
    Args:
        items (list): Items to display. Plain strings render as text rows;
            ``LayoutListBoxHeader`` objects (from ``gui_list_box_header``)
            render as collapsible section dividers.
        style (str): CSS-like style overrides for the listbox container.
        item_template (callable | None, optional): Called per item to build
            its row layout. Defaults to None (built-in text row).
        title_template (str | callable | None, optional): Title for the
            listbox. A string is used as-is; a callable is invoked to build
            the title row. Defaults to None.
        section_style (str | None, optional): Style overrides applied to each
            item row section. Defaults to None.
        title_section_style (str | None, optional): Style overrides applied to
            the title section. Defaults to None.
        select (bool, optional): Allow item selection. Defaults to ``False``.
        multi (bool, optional): Allow multiple simultaneous selections. Only
            used when ``select=True``. Defaults to ``False``.
        carousel (bool, optional): Use carousel styling (e.g. ship-type
            selection). Defaults to ``False``.
        collapsible (bool, optional): Clicking a header collapses items until
            the next header. Defaults to ``False``.
        read_only (bool, optional): Prevent item modification. Defaults to
            ``False``.
    
    Returns:
        LayoutListbox: The layout object created.
    
    Example:
        gui_list_box(items, style="area:0,0,100,100;", select=True)"""
def gui_message (layout_item, label=None):
    """Register a MAST label to run when a layout element receives a GUI event.
    
    Attaches a ``MessageTrigger`` to the current task so that when the engine
    fires a ``gui_message`` event matching ``layout_item``'s tag, the given
    label is pushed and executed inline. Used to respond to clicks on custom
    layout items (sections, regions, etc.) that are not plain buttons.
    
    Args:
        layout_item: The layout object whose tag to watch. Must expose
            ``is_message_for(event)`` (all standard layout items do).
        label (optional): MAST label or inline block to run on the event.
            Defaults to the current active label.
    
    Returns:
        MessageTrigger: The registered trigger object.
    
    Example:
        region = gui_region(style="area:10,10,50,50;")
        gui_message(region, on_region_click)
        ///on_region_click
            gui_text("Region clicked!")"""
def gui_panel_console_message (cid, left, top, width, height):
    ...
def gui_panel_console_message_list (cid, left, top, width, height):
    ...
def gui_panel_console_message_list_item (message_obj):
    ...
def gui_panel_console_message_tick (info_panel):
    ...
def gui_panel_ship_data_hide (cid, left, top, width, height):
    ...
def gui_panel_ship_data_show (cid, left, top, width, height):
    ...
def gui_panel_upgrade_list (cid, left, top, width, height):
    ...
def gui_panel_widget_hide (cid, left, top, width, height, widget):
    ...
def gui_panel_widget_show (cid, left, top, width, height, widget):
    ...
def gui_percent_from_pixels (client_id, pixels):
    """Convert a pixel size to GUI percentage coordinates for a client's screen.
    
    GUI layout positions are expressed as percentages (0–100) of the screen
    dimensions. Use this to convert a fixed pixel measurement to the equivalent
    percentage for a specific client's resolution.
    
    Args:
        client_id (int): The client whose screen resolution to use.
        pixels (float): The pixel size to convert.
    
    Returns:
        Vec3: Percentage values (x=horizontal %, y=vertical %, z=0).
    
    Example:
        pct = gui_percent_from_pixels(CLIENT_ID, 40)
        gui_section(style="height:{pct.y}%;")"""
def gui_represent (layout_item):
    """Redraw a layout item on the client screen.
    
    For sections and regions, recalculates the entire sub-layout and redraws
    all children. For individual items or rows, redraws that element only.
    
    Args:
        layout_item: The layout object to redraw.
    
    Example:
        gui_represent(my_section)"""
def gui_row (style=None):
    """Start a new layout row, pushing subsequent items to the next line.
    
    Call before adding items that should appear on a fresh row. Without
    explicit rows, items flow left-to-right across the current row.
    
    Args:
        style (str, optional): CSS-like style overrides for the row container.
            Defaults to None.
    
    Returns:
        Row: The row layout object.
    
    Example:
        gui_text("Name:")
        gui_row()
        gui_input("", var="ship_name")"""
def gui_sub_section (style=None):
    """Create a nested layout sub-section, used as a context manager.
    
    Sub-sections let you group and style a subset of content within the current
    section. Use with Python's ``with`` statement in MAST via the ``with``
    keyword. The sub-section is added to the current layout when the ``with``
    block exits.
    
    Args:
        style (str, optional): CSS-like style string controlling the column
            width, row height, background, etc. of the sub-section.
            Defaults to None.
    
    Returns:
        PageSubSection: Context manager object. Use with ``with``.
    
    Example:
        gui_row(style="row-height:3em;")
        with gui_sub_section(style="col-width:30%;"):
            gui_text("Left column")
        with gui_sub_section():
            gui_text("Right column")"""
def gui_tabbed_panel (items=None, style=None, tab=0, tab_location=0, icon_size=0):
    """Create a tabbed panel widget with icon-based tab navigation.
    
    Each tab is defined by a dict with ``path``, ``icon``, ``show``, and
    optionally ``hide`` and ``tick`` keys. The panel calls ``show`` when a tab
    is activated and ``hide`` when it is deactivated. Prefer ``gui_info_panel``
    for the standard info panel; use this directly only when building a custom
    panel layout.
    
    Args:
        items (list[dict], optional): Tab descriptors. Each dict has:
            ``path`` (str) — route name for this tab;
            ``icon`` (int) — icon index displayed on the tab button;
            ``show`` (callable) — ``show(cid, left, top, width, height)`` called
            when the tab becomes active;
            ``hide`` (callable, optional) — called when the tab is hidden;
            ``tick`` (callable, optional) — called each tick while the tab is
            active. Defaults to None.
        style (str, optional): CSS-like style string for the panel. Defaults to None.
        tab (int, optional): Index of the initially active tab. Defaults to 0.
        tab_location (int, optional): Edge where tabs appear (0=left). Defaults to 0.
        icon_size (int, optional): Icon size in pixels. Defaults to 0 (auto).
    
    Returns:
        TabbedPanel: The panel layout object.
    
    Example:
        panels = [
            {"path": "status", "icon": 140, "show": show_status, "hide": hide_status},
            {"path": "map",    "icon": 121, "show": show_map},
        ]
        tp = gui_tabbed_panel(panels, tab=0)"""
def gui_task_for_client (client_id):
    """Return the GUI task currently running for a client.
    
    Each connected client has a dedicated GUI task that drives its page layout.
    Returns ``None`` if the client has no active page.
    
    Args:
        client_id (int): The client to look up.
    
    Returns:
        MastAsyncTask | None: The client's GUI task, or ``None`` if unavailable.
    
    Example:
        task = gui_task_for_client(CLIENT_ID)
        if task is not None:
            ~~ task.set_variable("score", 10) ~~"""
def gui_text (props, style=None):
    """Add a text label to the current GUI layout.
    
    Args:
        props (str): Text content or property string, e.g. ``"Hello"`` or
            ``"$text:Hello;color:white;"``. Supports ``{var}`` interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Text: The layout item created.
    
    Example:
        gui_text("Hull: {hull_pct}%")
        gui_text("$text:WARNING;color:red;")"""
def panel_upgrade_item (message_obj):
    ...
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
class InfoButtonPromise(Promise):
    """class InfoButtonPromise"""
    def __init__ (self, message_data) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def set_result (self, result):
        ...
