from ...helpers import FrameContext


def gui_widget_list(console, widgets):
    """Set the engine console widget list for the current client.

    Sends a widget list string directly to the engine, replacing the current
    widget layout. Widgets are ``^``-separated engine widget names.

    Args:
        console (str): Console type name, e.g. ``"normal_helm"``.
        widgets (str): ``^``-separated list of engine widget names, e.g.
            ``"2dview^helm_movement^throttle"``.

    Example:
        gui_widget_list("normal_helm", "2dview^helm_movement^throttle")
    """    
    page = FrameContext.page
    if page is None:
        return None
    page.set_widget_list(console, widgets)

order_first_widgets = ["2dview","3dview", "comms_2d_view", "ship_internal_view", "weapon_2d_view", "science_2d_view"]
def gui_update_widget_list(add_widgets=None, remove_widgets=None):
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
        gui_update_widget_list(add_widgets="shield_control", remove_widgets="radar_zoom_ctrl")
    """    
    page = FrameContext.page
    if page is None:
        return None
    
    if add_widgets is None and remove_widgets is None:
        return
    if add_widgets is None:
        add_widgets = ""
    if remove_widgets is None:
        remove_widgets = ""

    widgets = set(page.widgets.split("^"))
    add_widgets = set(add_widgets.split("^"))
    remove_widgets = set(remove_widgets.split("^"))
    widgets = (widgets | add_widgets) - remove_widgets
    new_widgets = ""
    delim = ""
    for widget in widgets:
        if widget in order_first_widgets:
            new_widgets = widget + delim + new_widgets
            delim = "^"
        else:
            new_widgets = new_widgets + delim + widget
            delim = "^"
    #print(f"GUI {new_widgets} {widgets} {add_widgets} {remove_widgets}")
    FrameContext.context.sbs.send_client_widget_list(page.client_id, page.console, new_widgets)



def gui_update_widgets(add_widgets, remove_widgets):
    """Stage widget list changes on the pending widget list without sending.

    Modifies ``page.pending_widgets`` rather than the live widget list. Changes
    are committed when the pending list is flushed to the engine.

    Args:
        add_widgets (str): ``^``-separated widget names to add.
        remove_widgets (str): ``^``-separated widget names to remove.

    Example:
        gui_update_widgets("shield_control", "radar_zoom_ctrl")
    """    
    page = FrameContext.page
    if page is None:
        return None

    widgets = set(page.pending_widgets.split("^"))
    add_widgets = set(add_widgets.split("^"))
    remove_widgets = set(remove_widgets.split("^"))
    widgets = (widgets | add_widgets) - remove_widgets
    new_widgets = ""
    delim = ""
    for widget in widgets:
        if widget in order_first_widgets:
            new_widgets = widget + delim + new_widgets
            delim = "^"
        else:
            new_widgets = new_widgets + delim + widget
            delim = "^"
    
    page.pending_widgets = new_widgets



def gui_widget_list_clear():
    """Clear all engine widgets from the current client's console.

    Sends an empty widget list to the engine, removing all engine controls.
    The MAST GUI layout (sections, regions, etc.) is not affected.

    Example:
        gui_widget_list_clear()
    """    
    gui_widget_list("","")
from ...pages.layout.console_widget import ConsoleWidget
def gui_layout_widget(widget):
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
        gui_layout_widget("2dview")
    """    
    page = FrameContext.page
    if page is None:
        return None
    
    page.add_console_widget(widget)
    control = ConsoleWidget(widget)
    page.add_content(control, None)
    return control
    
