from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.icon import Icon


def gui_icon(props, style=None):
    """queue a gui icon element

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
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
    """queue a gui icon element

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
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

