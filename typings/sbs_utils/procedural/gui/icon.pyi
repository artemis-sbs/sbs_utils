from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.icon import Icon
from sbs_utils.pages.layout.icon_button import IconButton
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
