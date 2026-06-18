from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.dropdown import Dropdown

def gui_drop_down(props, style=None, var=None, data=None):
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
        gui_drop_down("items:Slow,Medium,Fast;", var="speed_setting")
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    props = task.compile_and_format_string(props)
    layout_item = Dropdown(tag, props)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()
    apply_control_styles(".dropdown", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item
