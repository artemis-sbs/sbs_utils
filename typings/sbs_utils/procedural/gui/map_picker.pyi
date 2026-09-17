from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def _map_item_template (item):
    """One carousel card: the map's display name over its description.
    
    gui_text_escape is not optional here. A description is free prose and a ``:`` or ``;``
    in it would otherwise be read as style properties, silently truncating the card."""
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
def gui_button (props, style=None, data=None, on_press=None, is_sub_task=None):
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
    
            **A callable is called with NOTHING unless it asks.** Declare a
            REQUIRED parameter and it is handed `data`; declare two and it gets
            `(data, event)`. Required parameters are the discriminator, never the
            parameter count -- the house idiom is a closure with bound defaults
            (`lambda _cid=client_id: go(_cid)`), which declares parameters that all
            have defaults and must keep being called with nothing::
    
                gui_button("Go", on_press=lambda _c=cid: fire(_c))   # -> ()
                gui_button("Go", on_press=shoot, data={"cid": cid})  # def shoot(data)
        is_sub_task (bool, optional): How an ``on_press`` **label** runs.
            ``True`` runs it as a sub-task: safe to press repeatedly, and it
            should end with ``->END``. ``False`` jumps the task that built the
            widget, so the press takes that task over and the handler must hand
            the console back -- this is the historical behavior and is
            **deprecated**. Defaults to None, meaning the library decides; a
            handler that paints a screen and reaches ``await gui()`` sends the
            GUI task there either way, so you should not need this.
    
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
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False, reveal=False, hint=None):
    """Add a listbox to the current GUI layout.
    
    Args:
        items (list): Items to display. Plain strings render as text rows;
            ``LayoutListBoxHeader`` objects (from ``gui_list_box_header``)
            render as collapsible section dividers.
        style (str): CSS-like style overrides for the listbox container.
    
            ``row-height`` is the height of ONE item row, and a FLOOR - a template
            that needs more grows past it. It also sizes the box each item is measured
            and drawn in, so a template whose rows declare no height fills the item
            rather than collapsing, and the item's CLICK REGION is never smaller than
            the row you can see.
    
            ``item-gap`` is the spacing BETWEEN items. This is what ``row-height``
            used to mean here, which made a list declaring the height its template
            already used render at twice the pitch.
    
            Declare neither and an item is exactly as tall as its template's rows,
            with items flush - unchanged from before either key existed.
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
        reveal (bool, optional): Scroll so the selected row is visible. A
            repaint rebuilds the listbox and the view starts at the top, so a
            restored selection can be held but off screen. Opt-in: this widget
            is load-bearing, and defaulting it on would move every list in every
            mission. Defaults to ``False``.
        hint (object, optional): An opaque token from the previous listbox's
            ``get_selection_hint()``. A repaint builds a DIFFERENT listbox whose
            view starts at the top, so without this the row under the user's
            mouse moves. Do not inspect it; pass it along.
    
    Returns:
        LayoutListbox: The layout object created.
    
    Example:
        gui_list_box(items, style="area:0,0,100,100;", select=True)"""
def gui_map_picker (maps=None, properties=True, title=None, start_text='Start', list_style='item-gap: 7em;'):
    """Build a map carousel plus a Start button; return an awaitable resolving to the choice.
    
    Pairs with ``map_start``: this one only CHOOSES, so a mission can do something else with
    the answer, or start a map it picked some other way.
    
        chosen = await gui_map_picker()
        map_start(chosen)
    
    Args:
        maps (list | None): Map labels to offer. Defaults to ``maps_get_list()``, which
            already hides maps whose ``if`` condition is false.
        properties (bool): Render the selected map's ``Properties:`` panel. On by default -
            it is two calls, and without it a map expecting ``PLAYER_COUNT`` starts with it
            unset, which is a silent wrong-behaviour trap rather than a missing feature.
        title (str | None): Listbox title. Defaults to a count of the maps.
        start_text (str): Label for the start button.
        list_style (str): Style string for the carousel.
    
    Returns:
        Promise: Resolves with the chosen map Label when Start is pressed. A story with no
        maps draws a message and returns a promise that never resolves, rather than raising."""
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
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x000002741D2A7A60>):
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
def map_apply_crew (map):
    """Publish a map's ``Crew:`` block for :func:`player_roster_apply`, OVERWRITING.
    
    WHY THIS IS NOT PART OF ``Defaults``. ``map_apply_defaults`` is set-if-absent, which
    is exactly right for seeding a control and exactly wrong here: an operator browsing
    the picker would pin whichever map they happened to look at FIRST, and every trial
    after it would be flown in that ship. So this always writes, and CLEARS the variables
    when the selected map declares no crew - leaving a stale hull behind is the same bug
    wearing a different hat.
    
    Reported from the Gamma with a Q playtest as "set the hull at mission select ... after
    Q's intro is too late and confuses people": a map that reshapes its crew from its own
    BODY does it after the console-select screen, so everyone spends that screen looking
    at a ship they are about to stop flying.
    
    Args:
        map (Label | None): The map label object (``None`` clears, so a picker with
            nothing selected does not keep the last map's crew)."""
def map_apply_defaults (map):
    """Apply a map's ``Defaults:`` metadata as SET-IF-ABSENT shared variables.
    
    For each ``VAR: value`` in the map's ``Defaults`` block, set the shared variable to
    ``value`` ONLY if it is not already set - so a value seeded by ``settings.yaml``, the
    story, or a loaded game code always wins (the same semantics as ``default shared``). This
    lets a map give its own Properties controls a starting value without promoting a map-local
    setting (e.g. a ``JOBS_SELECT`` only this map uses) to global settings or scattering
    ``default`` through the map body.
    
    The map's Properties panel renders (and binds its controls to SHARED scope) BEFORE the map
    body runs, so this must be applied at BOTH moments: when the panel is presented, AND again
    whenever the map is started as a task (AUTO_START and a headless ``--map`` runner start the
    map task without ever presenting the panel). It is idempotent - a map with no ``Defaults``
    is a no-op, and an already-set var is left untouched - so calling it at both points is safe.
    
    Args:
        map (Label): The map label object (``None`` is a no-op)."""
def map_get_properties (map):
    """Return the ``Properties`` inventory value of a map label.
    
    Checks ``"Properties"`` first, then ``"properties"`` as a fallback.
    
    Args:
        map (Label): The map label object.
    
    Returns:
        any: The properties value, or ``None`` if not set."""
def maps_get_list (include_hidden=False):
    """Return the ``@map`` labels defined in the current page's story.
    
    If only an ``__overview__`` label exists, it is returned as a single-item
    list. If no map labels are found at all, returns a placeholder list with a
    ``"No maps found"`` entry.
    
    Args:
        include_hidden (bool): When True, return conditional maps whose ``if`` is
            currently false as well. Callers that are RESOLVING A KNOWN MAP rather than
            offering a menu want this - ``game_code_decode`` looks a map up by path, and
            a saved code should not stop resolving because a condition happens to be
            false right now.
    
    Returns:
        list: ``@map`` Label objects, or a fallback list if none are defined."""
class _MapPickerPromise(Promise):
    """Presents the picker, and resolves with the CHOSEN MAP.
    
    Two jobs in one object, because neither alone works:
    
      * Queued gui_* widgets are not presented until a GuiPromise is polled
        (GuiPromise.initial_poll -> set_button_layout -> swap_layout). Returning a bare
        Promise would build a page that never appears - a silent failure, no error.
      * The obvious `promise_any(gui(), prom)` presents correctly but resolves with a
        LIST indexed by promise position (PromiseAllAny.result), so the caller gets
        `[None, ButtonResult]` where it wanted a map label, and `map_start` then fails
        deep inside map_apply_defaults.
    
    So: poll the GuiPromise for presentation, and carry the map as this promise's own
    result. `done()` is inherited - it is true as soon as a result is set."""
    def __init__ (self, gui_promise):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
