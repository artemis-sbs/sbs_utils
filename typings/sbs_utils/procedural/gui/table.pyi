from sbs_utils.helpers import FrameContext
def _cell (item, key):
    """Read a field from a row (dict, MastDataObject, or plain object)."""
def _disp (value):
    """Display text for a cell. An empty cell renders as a space rather than as
    nothing: a table reserves the row whether or not the cell has content, so a
    blank keeps the row height its neighbors have. The call site hands this to
    gui_text_escape, which does the ':'/';' quoting (#569 / #641)."""
def _resolve_columns (items, columns, font):
    """Normalize the column specs and turn every 'auto' width into a percent,
    sized to the widest measured cell and sharing the width the fixed columns
    leave free."""
def _set (item, key, value):
    """Write a field back to a row (dict, MastDataObject, or plain object)."""
def _widget_value (sender):
    """Read the current value from a control widget (get_value() or .value)."""
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
def gui_table (items, columns=None, style='row-height: 1.6em;', select=False, header=True, font='gui-2', on_cell_change=None, headers=None, **kwargs):
    """Add a table (a selectable/scrollable gui_list_box) to the layout.
    
    ``style`` is handed BOTH to the listbox and to each row's ``gui_row``. Under the
    old listbox semantics that meant a row of `row-height` and a GAP of the same, so
    every table rendered at twice its declared pitch; now both say the same thing and
    a table is as tall as it says.
    
    Two forms:
    
    **Block form** — author the row yourself, like the other containers::
    
        with gui_table(fleet, headers=["Ship", "Hull"], select=True) as ship:
            gui_text("{ship.name}")
            gui_text("{ship.hull}%")
    
    Each widget in the ``with`` block is a column; ``headers`` labels line up above
    them. (Used with ``with`` — pass no ``columns``.)
    
    **Declarative form** — pass column specs and it generates the row for you::
    
        gui_table(fleet, [{"key": "name", "label": "Ship"}, ...], select=True)
    
    Args:
        items: list of rows — dicts, MastDataObjects, or plain objects.
        columns: list of column specs (declarative form). Omit for the block form.
            Each spec is a dict:
            {"key": <field name>,
             "label": <header text>            (default: key),
             "align": "l" | "c" | "r"          (default: "l"),
             "width": <percent number> | "auto" (default: "auto"),
             "type": "text" | "checkbox" | "dropdown" | "input" | "button"
                                               (default: "text", read-only),
             "options": [...]                  (dropdown choices),
             "button_label": <text>}           (button cell label; default: label)
            Interactive cells write their new value back to the row and fire
            on_cell_change. 'auto' columns are sized to the widest cell (header +
            data) and share whatever percent the fixed columns leave.
        style: row style (row-height, padding, ...).
        select: allow row selection (default False).
        header: render the column-label header row (default True).
        font: cell/header font tag (default gui-2).
        on_cell_change: fn(item, key, value) called when a cell control changes
            (value is None for a button press). The row is already updated.
        **kwargs: forwarded to gui_list_box (multi, carousel, ...).
    
    Returns:
        The gui_list_box. Read the selected row with get_value()/get_selected().
    
    Example:
        gui_table(fleet, [
            {"key": "name",   "label": "Ship",    "align": "l"},
            {"key": "hull",   "label": "Hull",    "align": "c", "width": 20},
            {"key": "side",   "label": "Side",    "align": "r", "width": 20},
        ], select=True)"""
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
def measure_line_width (font, text):
    """Width in PIXELS of one unwrapped line, or None if unmeasurable."""
