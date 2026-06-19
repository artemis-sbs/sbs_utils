from sbs_utils.pages.layout.console_widget import ConsoleWidget
from sbs_utils.helpers import FrameContext
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
