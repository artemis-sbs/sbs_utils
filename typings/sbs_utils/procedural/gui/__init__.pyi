from sbs_utils.procedural.gui.gui import ButtonPromise
def gui (buttons=None, timeout=None):
    """Present the GUI layout that has been queued up for the current client.
    
    Suspends execution until the player presses a button or the timeout fires.
    GUI elements (text, images, sections, etc.) must be queued with ``gui_*``
    calls before ``await gui()``; they are rendered when the promise activates.
    
    Args:
        buttons (dict, optional): Extra buttons to add, mapping label text to
            jump target label name. e.g. ``{"Start": "start_label"}``.
            Defaults to None.
        timeout (Promise, optional): A promise (e.g. ``timeout_sim(30)``) that
            cancels the GUI when it resolves. Defaults to None.
    
    Returns:
        Promise: Resolves when a button is pressed or timeout fires.
    
    Example:
        gui_text("Choose your mission")
        await gui():
            + "Patrol":
                jump patrol_mission
            + "Escort":
                jump escort_mission"""
def gui_activate_console (console):
    """Set the current page's active console name.
    
    Marks the page as running a specific console type, which affects which
    console-specific routes and widgets respond to this client.
    
    Args:
        console (str): Console name, e.g. ``"helm"``, ``"weapons"``,
            ``"science"``.
    
    Example:
        gui_activate_console("helm")"""
def gui_add_console_type (path, display_name, description, label):
    """adds a tab definition
    
    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected"""
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
def gui_change (code, label):
    """Register a per-tick change watch on a Python expression.
    
    Evaluates ``code`` each tick and executes ``label`` when its value differs
    from the previous tick. Python equivalent of the MAST ``on change``
    construct. The trigger is attached to the current task and runs for as long
    as the task is active.
    
    Args:
        code (str): Python expression to evaluate each tick, e.g.
            ``"ship_speed > 100"``.
        label: MAST label or inline block to execute when the value changes.
    
    Example:
        gui_change("shield_level", shield_warning)
        ///shield_warning
            gui_text("Shields changed!")"""
def gui_checkbox (msg, style=None, var=None, data=None):
    """Add a checkbox to the current GUI layout.
    
    The current value of ``var`` (expected to be a bool) sets the initial
    checked state. When the player toggles the checkbox, ``var`` is updated.
    
    Args:
        msg (str): Label text or property string shown next to the checkbox,
            e.g. ``"Enable shields"`` or ``"$text:Active;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial checked state
            from and update on toggle. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Checkbox: The layout item created.
    
    Example:
        gui_checkbox("Enable auto-fire", var="auto_fire_on")"""
def gui_cinematic_auto (client_id):
    """Switch a client to cinematic view, automatically tracking its assigned ship.
    
    Sets the client's view mode to ``"3dview/front/cinematic"`` with automatic
    camera control. The tracked ship must expose excitement values; player ships
    have these set automatically.
    
    Args:
        client_id (int): The client to switch to cinematic view.
    
    Example:
        gui_cinematic_auto(CLIENT_ID)"""
def gui_cinematic_full_control (client_id, camera_id, camera_offset, tracked_id, tracked_offset):
    """Switch a client to cinematic view with explicit camera and target control.
    
    Sets the view mode to ``"3dview/front/cinematic"`` and hands full camera
    control to the caller. Both offset vectors are converted to engine
    ``vec3`` objects before being passed to ``cinematic_control``.
    
    Args:
        client_id (int): The client to switch to cinematic view.
        camera_id (int): Object ID to use as the camera position anchor.
        camera_offset (Vec3 | None): Offset from ``camera_id`` in world units.
            Pass ``None`` to use the object's origin.
        tracked_id (int): Object ID for the camera to look at.
        tracked_offset (Vec3 | None): Offset from ``tracked_id`` to look at.
            Pass ``None`` to use the object's origin.
    
    Example:
        gui_cinematic_full_control(CLIENT_ID, camera_ship_id, Vec3(0,50,0), target_id, None)"""
def gui_click (name_or_layout_item=None, label=None):
    """Register a click handler for a named element or layout item.
    
    Attaches a ``ClickableTrigger`` to the current task. When the element is
    clicked, sets ``__CLICKED__`` to the click tag and runs ``label`` inline
    (or as a sub-task if a different label is specified).
    
    Args:
        name_or_layout_item (str | layout object | None, optional): A click-tag
            string, a layout item exposing ``click_tag``, or ``None`` to match
            any click. Defaults to None.
        label (optional): MAST label to run on click. Defaults to the currently
            active label.
    
    Returns:
        ClickableTrigger: The registered trigger.
    
    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_click(btn, on_fire_pressed)
        ///on_fire_pressed
            ~~ fire_torpedo(SHIP_ID) ~~"""
def gui_client_id ():
    """Return the client ID for the currently executing GUI task.
    
    Shortcut for ``FrameContext.client_id``. Returns ``0`` when running on
    the server.
    
    Returns:
        int: Current client ID, or ``0`` for the server.
    
    Example:
        id = gui_client_id()
        gui_text("Your client ID is {id}")"""
def gui_clipboard_copy (s):
    """Write a text string to the Windows clipboard.
    
    Windows-only. Replaces whatever is currently on the clipboard.
    ``gui_clipboard_copy`` is an alias for this function.
    
    Args:
        s (str): The text to place on the clipboard.
    
    Example:
        gui_clipboard_put("TSN Artemis — Mission Report")"""
def gui_clipboard_get ():
    """Read the current text content of the Windows clipboard.
    
    Windows-only. Returns ``None`` if the clipboard is empty or contains
    non-text data.
    
    Returns:
        str | None: The clipboard text, or ``None`` if unavailable.
    
    Example:
        text = gui_clipboard_get()
        if text is not None:
            gui_text("Pasted: {text}")"""
def gui_clipboard_put (s):
    """Write a text string to the Windows clipboard.
    
    Windows-only. Replaces whatever is currently on the clipboard.
    ``gui_clipboard_copy`` is an alias for this function.
    
    Args:
        s (str): The text to place on the clipboard.
    
    Example:
        gui_clipboard_put("TSN Artemis — Mission Report")"""
def gui_console (console, is_jump=False):
    """Activate a standard console with its default engine widget layout.
    
    Sets the engine widget list for the named console using the built-in
    configuration. Supported values: ``"helm"``, ``"weapons"``,
    ``"science"``, ``"engineering"``, ``"comms"``, ``"cinematic"``,
    ``"mainscreen"``, ``"cockpit"``.
    
    Args:
        console (str): Console name (case-insensitive).
        is_jump (bool, optional): For ``"helm"`` only — include jump-drive
            controls in the widget list. Defaults to ``False``.
    
    Example:
        gui_console("helm")
        gui_console("helm", is_jump=True)"""
def gui_console_clients (path, for_ships=None):
    """Return the set of client IDs that have a specific console type.
    
    Searches all player ships (or the given ship set) for linked console
    clients whose role matches ``console,{path}``.
    
    Args:
        path (str): Console path to match, e.g. ``"helm"`` or ``"science"``.
        for_ships (object | None, optional): Agent ID, object, or set of ships
            to search. Defaults to all ``__player__`` ships.
    
    Returns:
        set: Client IDs that have a console matching ``path``.
    
    Example:
        helm_clients = gui_console_clients("helm")"""
def gui_content (content, style=None, var=None):
    """Place a Python widget object into the layout system.
    
    Wraps a pre-built Python widget (e.g. a ship picker, custom control) in a
    ``GuiControl`` so it participates in the normal layout flow.
    
    Args:
        content (widget): A Python GUI widget object.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to bind the widget's value to.
            The current value of ``var`` is pushed into the widget and updates
            flow back when the widget changes. Defaults to None.
    
    Returns:
        GuiControl: The layout wrapper object.
    
    Example:
        picker = ShipPicker(0, 0, "mast", "Your Ship")
        gui_content(picker, var="selected_ship")"""
def gui_drop_down (props, style=None, var=None, data=None):
    """Add a drop-down list to the current GUI layout.
    
    The current value of ``var`` sets the initially selected option. When the
    player selects an item, ``var`` is updated.
    
    Args:
        props (str): Semicolon-separated option list and optional properties,
            e.g. ``"items:Red,Green,Blue;"`` or ``"$items:Red,Green;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Dropdown: The layout item created.
    
    Example:
        gui_drop_down("items:Slow,Medium,Fast;", var="speed_setting")"""
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
def gui_get_console_type (key):
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_get_console_type_list ():
    """Get the list of consoles defined by @console decorator labels
    path is added as a value"""
def gui_get_console_types ():
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_hide (layout_item):
    """Hide a visible layout item.
    
    For sections, recalculates the layout after hiding. For individual items
    or rows, hides the element but does not re-layout — pair with
    ``gui_represent`` on the parent section if the layout needs updating.
    
    Args:
        layout_item: The layout object to hide. No-op if already hidden or
            ``None``.
    
    Example:
        gui_hide(warning_row)
        gui_represent(my_section)"""
def gui_hide_choice ():
    """Hide the button that was just pressed during its handler block.
    
    Call this from inside a button's handler block to remove the button
    from the layout immediately after it is clicked, without waiting for
    the ``await gui()`` to complete. Has no effect if called outside of
    a running button handler.
    
    Example:
        await gui():
            + "Launch Missile":
                gui_hide_choice()
                ~~ fire_torpedo(SHIP_ID) ~~"""
def gui_history_back ():
    """Jump back to the previous navigation history entry.
    
    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no history.
    
    Example:
        * "Back"
            gui_history_back()"""
def gui_history_clear ():
    """Clear the navigation history for the current page.
    
    Removes all back and forward history entries. Call this when entering a
    top-level screen where back-navigation should not be available.
    
    Example:
        gui_history_clear()"""
def gui_history_forward ():
    """Jump forward to the next navigation history entry.
    
    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no forward history.
    
    Example:
        * "Forward"
            gui_history_forward()"""
def gui_history_jump (to_label, back_name=None, back_label=None, back_data=None):
    """Jump to a new GUI label and record the current position in navigation history.
    
    Appends the current position to the back-stack (clearing any forward
    history) then jumps to ``to_label``. Call ``gui_history_back`` to return.
    
    Args:
        to_label (label): Label to navigate to.
        back_name (str | None, optional): Display name for the back entry.
            Defaults to ``"BACK"``.
        back_label (label | None, optional): Label to return to. Defaults to
            the currently active label.
        back_data (dict | None, optional): Variables to restore when returning
            back. Defaults to None.
    
    Returns:
        PollResults: Result of the jump.
    
    Example:
        gui_history_jump(ship_detail_screen, back_name="Ship List")"""
def gui_history_redirect (back_name=None, back_label=None, back_data=None):
    """Append to navigation history without jumping forward.
    
    Adds a history entry so the current location can be returned to via
    ``gui_history_back``, but does not change the active label. Use when you
    need to update the back-stack from within a label that was jumped to
    externally (e.g. from a route).
    
    Args:
        back_name (str | None, optional): Display name for the history entry.
            Defaults to ``"BACK"``.
        back_label (label | None, optional): Label to return to. Defaults to
            the currently active label.
        back_data (dict | None, optional): Variables to restore when returning
            back. Defaults to None."""
def gui_history_store (back_text, back_label=None):
    """Record the current label as a history entry (back destination).
    
    Stores the active label (or ``back_label``) so that ``gui_history_back``
    can return to it later. Use ``gui_history_jump`` instead when also
    navigating forward.
    
    Args:
        back_text (str): Display name for this history entry (shown in back
            buttons or breadcrumbs).
        back_label (label, optional): Label to return to. Defaults to the
            currently active label."""
def gui_hole (count=1, style=None):
    """Reserve empty column space that the next layout item expands to fill.
    
    Unlike ``gui_blank``, a hole is consumed by the following item as extra
    width. Use it to make a single element span multiple column slots.
    
    Args:
        count (int, optional): Number of extra column slots to reserve.
            Defaults to 1.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Hole: The last hole layout item created.
    
    Example:
        gui_hole(2)
        gui_text("This text spans 3 columns")"""
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
def gui_icon_button (props, style=None):
    """Add a clickable icon button to the current GUI layout.
    
    Like ``gui_icon`` but the rendered item accepts click events.
    
    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/fire"`` or ``"image:icons/fire;color:red;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        IconButton: The layout item created.
    
    Example:
        btn = gui_icon_button("icons/fire")
        gui_click(btn, on_fire_clicked)"""
def gui_image (props, style=None, fit=0):
    """Add an image to the current GUI layout.
    
    Resolves the image via the atlas, mission directory, and engine graphics
    path in that order. Prefer the named wrappers (``gui_image_stretch``,
    ``gui_image_absolute``, etc.) over calling this directly.
    
    Args:
        props (str): Image filename (without extension), a registered atlas
            key (see ``gui_image_add_atlas``), or an image property string
            like ``"image:media/logo;color:white;"``. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
        fit (int, optional): Scaling mode — 0=stretch, 1=absolute pixels,
            2=keep aspect ratio (top-left), 3=keep aspect ratio (centered).
            Defaults to 0.
    
    Returns:
        Image: The layout item created."""
def gui_image_absolute (props, style=None):
    """Add an image to the layout at its native pixel dimensions.
    
    The image is drawn at 1:1 pixel size relative to the client's screen
    resolution, anchored at the top-left of the layout area.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_absolute("media/icons/torpedo")"""
def gui_image_add_atlas (key, image, left=None, top=None, right=None, bottom=None):
    """The image atlas allows a key name to be used to assign to a set of image properties.
    This key can be used instead of image properties in any command that expect image properties.
    
    The image file passed will be used to search for the file. It will first check the mission directory followed by data/graphics folder.
    In the future this could be modified to account for mods, e.g. a common media folders.
    The image atlas takes care of supplying the correct path for the engine to use.
    
    By specifying the rect (left,top, right, bottom) the image key can reference a part of an image.
    
    
    Add a key to reference a full image
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image_add_atlas("test", "media/LegendaryMissions/operator")
    ```
    
    Add a key to reference a full image
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image_add_atlas("test2", "media/LegendaryMissions/operator", 645,570, 950,820)
    ```
    
    Once the atlas is added the key can be used anywhere images can be used.
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image("test")
    ```
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    # Text area also use the image atlas for images
    gui_text_area("![](image://test2?scale=0.5&fill=center)")
    ```
    
    
    
    Args:
        key (str): the key to define in the image atlas
        image (str): The file of the image. This can also be a image property string do not include the extension. Only PNG files are valid.
        left (float, optional): The pixel location of the left. Defaults to None.
        top (float, optional): The pixel location of the top. Defaults to None.
        right (float, optional): The pixel location of the right. Defaults to None.
        bottom (float, optional): The pixel location of the bottom. Defaults to None.
    
    Returns:
        ImageAtlas: The image Atlas object. This is a low level object typically used by the system """
def gui_image_get_atlas (text):
    ...
def gui_image_keep_aspect_ratio (props, style=None):
    """Add an image scaled to fit the area while preserving aspect ratio.
    
    Scales the image as large as possible without cropping, anchored
    top-left. Leaves empty space if the area's aspect ratio differs from
    the image's.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_keep_aspect_ratio("media/ship/artemis")"""
def gui_image_keep_aspect_ratio_center (props, style=None):
    """Add an image scaled to fit the area while preserving aspect ratio, centered.
    
    Like ``gui_image_keep_aspect_ratio`` but centers the image in the
    remaining space when the aspect ratios differ.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_keep_aspect_ratio_center("media/crew/captain")"""
def gui_image_size (file):
    """Return the pixel dimensions of an image file or atlas entry.
    
    Checks the atlas first, then reads the PNG header directly. Results are
    cached so repeated calls are free after the first read.
    
    Args:
        file (str): Atlas key or image path (without ``.png`` extension).
    
    Returns:
        tuple[int, int]: ``(width, height)`` in pixels, or ``(-1, -1)`` if
            the file cannot be read.
    
    Example:
        w, h = gui_image_size("media/backgrounds/nebula")"""
def gui_image_stretch (props, style=None):
    """Add an image to the layout, stretched to fill its area.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string e.g. ``"image:media/logo;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_stretch("media/backgrounds/nebula")"""
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
def gui_input (props, style=None, var=None, data=None):
    """Add a text input field to the current GUI layout.
    
    The current value of ``var`` is pre-filled as the input text. When the
    player edits and submits, ``var`` is updated with the new value.
    
    Args:
        props (str): Property string for input configuration, e.g.
            ``"hint:Enter name;"`` or ``""`` for defaults.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to pre-fill and update on submit.
            Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        TextInput: The layout item created.
    
    Example:
        gui_input("", var="ship_name", style="col-width:50%;")"""
def gui_int_slider (msg, style=None, var=None, data=None):
    """Add an integer-only slider control to the current GUI layout.
    
    Convenience wrapper for ``gui_slider(..., is_int=True)``.
    
    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"min:1;max:10;label:Count;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial value from and
            update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Slider: The layout item created.
    
    Example:
        gui_int_slider("min:1;max:5;label:Torpedo Count;", var="torp_count")"""
def gui_layout_widget (widget):
    """Place a specific engine widget at a fixed position in the layout.
    
    Adds the named engine widget to the console widget list AND places a
    ``ConsoleWidget`` placeholder in the layout at the current position so the
    engine widget renders inside the defined area.
    
    Args:
        widget (str): Engine widget name, e.g. ``"2dview"`` or
            ``"helm_movement"``.
    
    Returns:
        ConsoleWidget: The layout placeholder item.
    
    Example:
        gui_section(style="area:0,0,70,100;")
        gui_layout_widget("2dview")"""
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
def gui_list_box_header (label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
    """Create a collapsible section header for use in a listbox.
    
    When ``collapsible=True`` is set on the listbox, clicking a header toggles
    the visibility of items that follow it until the next header.
    
    Args:
        label (str): Header label text.
        collapse (bool, optional): Start in collapsed state. Defaults to
            ``False``.
        indent (int, optional): Logical indent level for tree structures.
            Defaults to 0.
        selectable (bool, optional): Whether clicking the header fires a
            selection event in addition to toggling collapse. Defaults to
            ``False``.
        data (object, optional): Arbitrary data attached to the header item.
            Defaults to None.
        visual_indent (int | None, optional): Override indent level for
            rendering only. Defaults to None (uses ``indent``).
    
    Returns:
        LayoutListBoxHeader: The header item."""
def gui_list_box_is_header (item):
    """Return whether a listbox item is a collapsible header.
    
    Args:
        item: Any item from a listbox items list.
    
    Returns:
        bool: ``True`` if the item is a ``LayoutListBoxHeader``.
    
    Example:
        for item in items:
            if gui_list_box_is_header(item):
                ~~ print("header:", item.label) ~~"""
def gui_listbox_items_convert_headers (items):
    """Convert a flat string list into a listbox-ready list with collapsible headers.
    
    Items prefixed with ``>>`` become ``LayoutListBoxHeader`` objects; all
    others pass through as plain strings. Pass the result to ``gui_list_box``
    with ``collapsible=True`` to enable collapse on header click.
    
    Args:
        items (list[str]): Flat list of strings. Prefix a string with ``>>``
            to make it a collapsible header, e.g. ``">>Section A"``.
    
    Returns:
        list[str | LayoutListBoxHeader]: Mixed list ready for ``gui_list_box``.
    
    Example:
        items = gui_listbox_items_convert_headers(
            [">>Section A", "Item 1", "Item 2", ">>Section B", "Item 3"]
        )
        gui_list_box(items, style="", select=True, collapsible=True)"""
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
def gui_message_callback (layout_item, cb):
    """Set a Python callable to invoke when a layout element receives a GUI event.
    
    Attaches a callback directly to the layout item's ``on_message_cb``
    attribute. The callback is called with the event and the layout item when
    the engine fires a ``gui_message`` event matching the item's tag.
    Use this for pure-Python handlers; use ``gui_message`` for MAST label
    handlers.
    
    Args:
        layout_item: The layout object to attach the callback to.
        cb (callable): Function called as ``cb(event, layout_item)`` on event.
    
    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_message_callback(btn, lambda e, item: fire_torpedo(SHIP_ID))"""
def gui_message_label (layout_item, label):
    """Schedule a MAST label as a sub-task when a layout element receives a GUI event.
    
    Similar to ``gui_message_callback`` but wraps the label in a
    ``gui_sub_task_schedule`` call, running it as an independent sub-task
    rather than inline in the current task.
    
    Args:
        layout_item: The layout object to attach the handler to.
        label: MAST label to schedule as a sub-task on event.
    
    Example:
        section = gui_sub_section(style="col-width:30%;")
        gui_message_label(section, handle_section_click)"""
def gui_panel_console_message (cid, left, top, width, height):
    ...
def gui_panel_console_message_list (cid, left, top, width, height):
    ...
def gui_panel_console_message_tick (info_panel):
    ...
def gui_panel_upgrade_list (cid, left, top, width, height):
    ...
def gui_panel_widget_hide (cid, left, top, width, height, widget):
    ...
def gui_panel_widget_show (cid, left, top, width, height, widget):
    ...
def gui_percent_from_ems (client_id, ems, font):
    """Convert an em-based size to GUI percentage coordinates for a client's screen.
    
    An em is the width/height of the character "X" in the given font. Use this
    to size layout elements relative to text size rather than fixed pixels.
    
    Args:
        client_id (int): The client whose screen resolution to use.
        ems (float): The number of em units to convert.
        font (str): Font name used to measure one em (e.g. ``"hud_font"``).
    
    Returns:
        Vec3: Percentage values (x=horizontal %, y=vertical %, z=0).
    
    Example:
        pct = gui_percent_from_ems(CLIENT_ID, 2, "hud_font")
        gui_section(style="width:{pct.x}%;")"""
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
def gui_properties_change (var, label):
    """Watch a MAST variable and run an inline block when its value changes.
    
    Registers a per-tick change detector on the current client's GUI task.
    When ``var`` changes value, the block at ``label`` is pushed and executed
    immediately within the current tick.
    
    Args:
        var (str): Name of the MAST variable to watch.
        label: The inline label or block to execute on change.
    
    Example:
        gui_properties_change("shield_level", shield_changed)
        ///shield_changed
            gui_text("Shields: {shield_level}")"""
def gui_properties_set (p=None, tag=None):
    """Update the data displayed in a property list box.
    
    Parses ``p`` (a dict or YAML string) into a flat list of label/control
    pairs and refreshes the list box stored under ``tag`` in the GUI task.
    Call this whenever the underlying data changes to redraw the panel.
    
    Args:
        p (dict | str, optional): Property data as a Python dict or a YAML
            string. Dict keys become labels; values are Python expressions
            evaluated to produce the control widget. Nested dicts become
            collapsible sections. Defaults to None (clears the list).
        tag (str, optional): Task inventory key holding the list box widget.
            Defaults to ``"__PROPS_LB__"``.
    
    Example:
        gui_properties_set({"Speed": "gui_text(str(ship_speed))", "Shields": "gui_slider(shield_pct)"})"""
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x00000215CB1C9BC0>):
    """Create a property list box with single-line label/control layout.
    
    Each property is rendered as a label on the left and its control widget
    on the right of the same row. Suitable for compact property panels.
    The widget is stored in the GUI task under ``tag`` so ``gui_properties_set``
    can refresh it later.
    
    Args:
        name (str, optional): Title shown in the list box header.
            Defaults to ``"Properties"``.
        tag (str, optional): Task inventory key used to store and retrieve
            the list box widget. Defaults to ``"__PROPS_LB__"``.
        temp (callable, optional): Item template function used to render each
            row. Defaults to the built-in one-line template.
    
    Returns:
        LayoutListBox: The list box widget.
    
    Example:
        gui_property_list_box("Navigation")
        gui_properties_set({"Heading": "gui_text(str(heading))", "Speed": "gui_text(str(speed))"})"""
def gui_property_list_box_stacked (name=None, tag=None):
    """Create a property list box with two-line stacked label/control layout.
    
    Each property is rendered as a label on one line and its control widget
    on the line below. Useful when controls are wide and need their own row.
    The widget is stored in the GUI task under ``tag`` so ``gui_properties_set``
    can refresh it later.
    
    Args:
        name (str, optional): Title shown in the list box header.
            Defaults to ``"Properties"``.
        tag (str, optional): Task inventory key used to store and retrieve
            the list box widget. Defaults to ``"__PROPS_LB__"``.
    
    Returns:
        LayoutListBox: The list box widget.
    
    Example:
        gui_property_list_box_stacked("Ship Systems")
        gui_properties_set({"Warp Core": "gui_slider(warp_pct)"})"""
def gui_radio (msg, style=None, var=None, data=None, vertical=False):
    """Add a radio button group to the current GUI layout.
    
    The current value of ``var`` sets the initially selected option. When the
    player selects a button, ``var`` is updated to the selected label.
    
    Args:
        msg (str): Comma-separated button labels or property string, e.g.
            ``"Alpha,Beta,Gamma"`` or ``"items:Slow,Fast;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on selection. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
        vertical (bool, optional): Stack buttons vertically. Defaults to
            ``False`` (horizontal).
    
    Returns:
        RadioButtonGroup: The layout item created.
    
    Example:
        gui_radio("Beam,Missile,Mine", var="weapon_type")"""
def gui_rebuild (region):
    """Mark a section or region to rebuild its layout on the next present.
    
    Clears the region's sub-layout so it is reconstructed from scratch the
    next time the region is rendered.
    
    Args:
        region: A section or region layout item.
    
    Returns:
        The same ``region`` object, for chaining.
    
    Example:
        gui_rebuild(my_region)
        gui_represent(my_region)"""
def gui_refresh (label):
    """Re-run an ``await gui()`` block at a given label on the current task.
    
    Causes any scheduler running ``label`` to rebuild its GUI from scratch on
    the next tick.
    
    Args:
        label: MAST label whose ``await gui()`` block should be refreshed.
            Pass ``None`` to refresh the current task's active label.
    
    Example:
        gui_refresh(status_panel)"""
def gui_region (style=None):
    """Create a re-representable GUI region pinned to an absolute screen area.
    
    Unlike ``gui_sub_section``, a region uses absolute positioning (the ``area``
    style property) and can be redrawn independently with ``region.represent()``.
    Use it for UI panels that update without redrawing the entire page.
    Also a context manager — content inside the ``with`` block is placed in
    the region.
    
    Args:
        style (str, optional): CSS-like style string. The ``area:`` property
            sets the absolute screen position (left, top, right, bottom %).
            Defaults to None.
    
    Returns:
        PageRegion: Context manager object with ``show()``, ``rebuild()``,
            and ``represent()`` methods.
    
    Example:
        hud = gui_region(style="area:0,0,100,10;")
        with hud:
            gui_text("HUD content here")
        ~~ hud.represent(event) ~~   # refresh just this region later"""
def gui_remove_console_type (path, display_name, label):
    """adds a tab definition
    
    Args:
        path (str): Console path
        display_name (str): Display name
        label (label): Label to run when tab selected"""
def gui_represent (layout_item):
    """Redraw a layout item on the client screen.
    
    For sections and regions, recalculates the entire sub-layout and redraws
    all children. For individual items or rows, redraws that element only.
    
    Args:
        layout_item: The layout object to redraw.
    
    Example:
        gui_represent(my_section)"""
def gui_request_client_string (client_id, key, timeout=None):
    """Request a text string from the player via a native OS input dialog.
    
    Sends a ``request_client_string`` call to the engine for the given client.
    The engine shows an OS-level text input and returns the typed value as a
    ``client_string`` event. Suspends until the player submits or the timeout
    fires.
    
    Args:
        client_id (int): Client to prompt.
        key (str): Tag used to identify the response event (``event.sub_tag``).
        timeout (Promise, optional): A promise that cancels the request if it
            resolves first. Defaults to None.
    
    Returns:
        Promise: Resolves with the typed string as its result.
    
    Example:
        result = await gui_request_client_string(CLIENT_ID, "ship_name")
        ~~ player_name = result.result ~~"""
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
def gui_reroute_clients (label, data=None, exclude=None):
    """Jump all connected client GUI tasks to a new label.
    
    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on each task before
            jumping. Defaults to None.
        exclude (set | None, optional): Set of client IDs to skip. Defaults
            to None (no exclusions).
    
    Example:
        gui_reroute_clients(mission_end_screen, exclude={spectator_id})"""
def gui_reroute_server (label, data=None):
    """Jump the server GUI task to a new label.
    
    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.
    
    Example:
        gui_reroute_server(server_status_page)"""
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
def gui_screen_size (client_id):
    """Return the pixel dimensions of a client's screen.
    
    Args:
        client_id (int): The client whose screen to query.
    
    Returns:
        Vec3: Screen dimensions in pixels (x=width, y=height, z=0).
    
    Example:
        size = gui_screen_size(CLIENT_ID)
        ~~ print(size.x, size.y) ~~"""
def gui_screenshot (image_path):
    """Capture the full desktop and save it as a BMP file.
    
    Windows-only. Captures the entire desktop window (not just the Cosmos
    window) using GDI BitBlt. Useful for automated testing or recording
    mission state.
    
    Args:
        image_path (str): Absolute path to write the ``.bmp`` file.
    
    Example:
        ~~ gui_screenshot("C:/missions/debug/frame001.bmp") ~~"""
def gui_section (style=None):
    """Create a top-level GUI layout section at a specific screen area.
    
    Sections are the primary way to position content on screen. The ``area``
    style property sets the region (left, top, right, bottom as percentages).
    Content added after this call is placed inside the section until the next
    ``gui_section`` or the frame ends.
    
    Args:
        style (str, optional): CSS-like style string. Use ``area:`` to position
            the section, e.g. ``"area:10,10,90,90;"``. Defaults to None.
    
    Returns:
        Layout: The layout object for this section.
    
    Example:
        gui_section(style="area:5,5,95,50;")
        gui_text("Top half of screen")
        gui_section(style="area:5,50,95,95;")
        gui_text("Bottom half of screen")"""
def gui_set_style_def (name, style):
    """Parse a style string and register it under a named class.
    
    After registering, the name can be used as a CSS class reference in any
    style string (e.g. ``".my_style"``).
    
    Args:
        name (str): Class name to register (conventionally prefixed with
            ``"."``), e.g. ``".alert"``.
        style (str): CSS-like style string to associate with the name.
    
    Returns:
        StyleDefinition: The parsed and registered style object.
    
    Example:
        gui_set_style_def(".alert", "color:red;background:#400;")
        gui_text("Warning!", style=".alert")"""
def gui_ship (props, style=None):
    """Render a 3D ship model in the current GUI layout.
    
    Displays a real-time 3D render of the named ship type within the layout
    area. The ship type key must match one defined in the game data.
    
    Args:
        props (str): Ship type key or property string, e.g. ``"battleship"``
            or ``"$type:cruiser;angle:45;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Ship: The layout item created.
    
    Example:
        gui_ship("battleship", style="area:20,0,80,60;")"""
def gui_show (layout_item):
    """Make a hidden layout item visible.
    
    For sections, recalculates the layout after showing. For individual items
    or rows, shows the element but does not re-layout — pair with
    ``gui_represent`` on the parent section if the layout needs updating.
    
    Args:
        layout_item: The layout object to show. No-op if already visible or
            ``None``.
    
    Example:
        gui_show(warning_row)
        gui_represent(my_section)"""
def gui_slider (msg, style=None, var=None, data=None, is_int=False):
    """Add a slider control to the current GUI layout.
    
    The current value of ``var`` is used as the initial slider position. When
    the player adjusts the slider, ``var`` is updated.
    
    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"min:0;max:100;label:Energy;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial value from and
            update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
        is_int (bool, optional): Restrict values to integers. Defaults to
            ``False``.
    
    Returns:
        Slider: The layout item created.
    
    Example:
        gui_slider("min:0;max:100;label:Speed;", var="speed_pct")"""
def gui_style_def (style):
    """Parse a CSS-like style string into a StyleDefinition object.
    
    Useful when you want to pre-parse a style string and inspect or reuse
    it without re-parsing each time.
    
    Args:
        style (str): CSS-like style string, e.g. ``"color:red;col-width:50%;"``.
    
    Returns:
        StyleDefinition: Parsed style object.
    
    Example:
        s = gui_style_def("color:green;font:hud_font;")"""
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
def gui_text_area (props, style=None):
    """Add a rich text area to the current GUI layout.
    
    Supports Markdown-style formatting and inline image references
    (``![](image://key)``). Use for multi-line or formatted text blocks.
    
    Args:
        props (str): Text content or Markdown string. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        TextArea: The layout item created.
    
    Example:
        gui_text_area("## Status\nAll systems nominal.")
        gui_text_area("![](image://logo?scale=0.5) Mission active")"""
def gui_update (tag, props, shared=False, test=None):
    """Update the property string of an existing GUI element by tag.
    
    Finds the element with the given tag on the current page (or all pages if
    ``shared=True``) and updates its properties in-place without rebuilding the
    full layout.
    
    Args:
        tag (str): The element tag to find and update.
        props (str): New property string for the element, e.g.
            ``"$text:Firing!;color:red;"``.
        shared (bool, optional): Apply the update to all client pages, not just
            the current one. Defaults to ``False``.
        test (dict | None, optional): Only apply the update when any variable
            in ``test`` has changed since the last update. Defaults to None
            (always update).
    
    Example:
        gui_update(status_tag, "$text:OK;color:green;")"""
def gui_update_shared (tag, props, test=None):
    """Update a GUI element by tag on all client pages.
    
    Convenience wrapper for ``gui_update(tag, props, shared=True, test=test)``.
    
    Args:
        tag (str): The element tag to find and update.
        props (str): New property string for the element.
        test (dict | None, optional): Only update when any variable in
            ``test`` has changed. Defaults to None.
    
    Example:
        gui_update_shared(alert_tag, "$text:ALERT;color:red;")"""
def gui_update_widget_list (add_widgets=None, remove_widgets=None):
    """Add or remove widgets from the current client's active widget list.
    
    Modifies the live widget list by taking the union of ``add_widgets`` and
    the current list, then subtracting ``remove_widgets``. View widgets
    (``2dview``, ``3dview``, etc.) are always placed first.
    
    Args:
        add_widgets (str | None, optional): ``^``-separated widget names to
            add. Defaults to None (no additions).
        remove_widgets (str | None, optional): ``^``-separated widget names to
            remove. Defaults to None (no removals).
    
    Example:
        gui_update_widget_list(add_widgets="shield_control", remove_widgets="radar_zoom_ctrl")"""
def gui_update_widgets (add_widgets, remove_widgets):
    """Stage widget list changes on the pending widget list without sending.
    
    Modifies ``page.pending_widgets`` rather than the live widget list. Changes
    are committed when the pending list is flushed to the engine.
    
    Args:
        add_widgets (str): ``^``-separated widget names to add.
        remove_widgets (str): ``^``-separated widget names to remove.
    
    Example:
        gui_update_widgets("shield_control", "radar_zoom_ctrl")"""
def gui_vradio (msg, style=None, var=None, data=None):
    """Add a vertical radio button group to the current GUI layout.
    
    Convenience wrapper for ``gui_radio(..., vertical=True)``.
    
    Args:
        msg (str): Comma-separated button labels or property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on selection. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        RadioButtonGroup: The layout item created.
    
    Example:
        gui_vradio("Alpha,Beta,Gamma", var="choice")"""
def gui_widget_list (console, widgets):
    """Set the engine console widget list for the current client.
    
    Sends a widget list string directly to the engine, replacing the current
    widget layout. Widgets are ``^``-separated engine widget names.
    
    Args:
        console (str): Console type name, e.g. ``"normal_helm"``.
        widgets (str): ``^``-separated list of engine widget names, e.g.
            ``"2dview^helm_movement^throttle"``.
    
    Example:
        gui_widget_list("normal_helm", "2dview^helm_movement^throttle")"""
def gui_widget_list_clear ():
    """Clear all engine widgets from the current client's console.
    
    Sends an empty widget list to the engine, removing all engine controls.
    The MAST GUI layout (sections, regions, etc.) is not affected.
    
    Example:
        gui_widget_list_clear()"""
