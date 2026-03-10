from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.text_input import TextInput
import re

def gui_input(props, style=None, var=None, data=None):
    """ Draw a text type in

    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    if props is not None:
        props = task.compile_and_format_string(props)
    else:
        props = ""

    val = ""
    if var is not None:
        val = task.get_variable(var, "")

    if "$text:" not in props:
        sanitized_text = re.sub(r"[^A-Za-z0-9 \-_']", "", val)
        if var is not None and sanitized_text != val:
            task.set_variable(var, sanitized_text)
        props = f"$text:{sanitized_text};{props}"

    layout_item = TextInput(tag, props)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    apply_control_styles(".input", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item
