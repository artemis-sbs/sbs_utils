from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.layout_listbox import LayoutListbox, LayoutListBoxHeader



def gui_listbox_items_convert_headers(items):
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
        gui_list_box(items, style="", select=True, collapsible=True)
    """
    ret = []
    for k in items:
        if isinstance(k,str):
            collapse = False
            if k.startswith(">>"):
                k = k[2:]
                ret.append(LayoutListBoxHeader(k, collapse))
            else:
                ret.append(k)
    return ret

def gui_list_box_is_header(item):
    """Return whether a listbox item is a collapsible header.

    Args:
        item: Any item from a listbox items list.

    Returns:
        bool: ``True`` if the item is a ``LayoutListBoxHeader``.

    Example:
        for item in items:
            if gui_list_box_is_header(item):
                ~~ print("header:", item.label) ~~
    """
    return isinstance(item, LayoutListBoxHeader)


def gui_list_box_header(label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
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
        LayoutListBoxHeader: The header item.
    """
    return LayoutListBoxHeader(label, collapse, indent, selectable, data, visual_indent)

def gui_list_box(items, style,
                 item_template=None, title_template=None,
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False,  collapsible=False,read_only=False):
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
        gui_list_box(items, style="area:0,0,100,100;", select=True)
    """
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    # The gui_content sets the values
    layout_item = LayoutListbox(0, 0, tag, items,
                 item_template, title_template, 
                 section_style, title_section_style,
                 select,multi, carousel,  collapsible, read_only)
    # #layout_item.data = data
    # if var is not None:
    #     layout_item.var_name = var
    #     layout_item.var_scope_id = task.get_id()
    #     layout_item.update_variable()

    apply_control_styles(".listbox", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


