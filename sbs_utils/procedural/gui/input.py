from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.text_input import TextInput
def gui_input(props, style=None, var=None, data=None):
    """Add a text input field to the current GUI layout.

    The current value of ``var`` is pre-filled as the input text. When the
    player edits and submits, ``var`` is updated with the new value.

    Args:
        props (str): Property string for input configuration, e.g.
            ``"hint:Enter name;"`` or ``""`` for defaults.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to pre-fill and update on submit.
            Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.

    Returns:
        TextInput: The layout item created.

    Example:
        gui_input("", var="ship_name", style="col-width:50%;")
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
        # Wrap the value in backticks so any ':' or ';' in it is treated as
        # literal text rather than a style delimiter (issue #569). An EMPTY
        # value must NOT be wrapped: `` renders as a stray ` in the box
        # (issue #641) which then seeds the #569 corruption once the player
        # types into it.
        if val:
            props = f"$text:`{val}`;{props}"
        else:
            props = f"$text:;{props}"

    layout_item = TextInput(tag, props)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    apply_control_styles(".input", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item
