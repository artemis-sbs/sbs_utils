from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.icon import Icon


def gui_icon(props, style=None):
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
        gui_text("{shield_pct}%")
    """        
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = Icon(tag,props)
    apply_control_styles(".icon", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

from ...pages.layout.icon_button import IconButton
def gui_icon_button(props, style=None):
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
        gui_click(btn, on_fire_clicked)
    """        
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = IconButton(tag,props)
    apply_control_styles(".icon_button", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

