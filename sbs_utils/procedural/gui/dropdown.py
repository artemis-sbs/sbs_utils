from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.dropdown import Dropdown

def gui_drop_down(props, style=None, var=None, data=None):
    """Add a drop-down list to the current GUI layout.

    When the player selects an item, ``var`` is updated. ``var`` is written, not
    read: the INITIAL selection comes from ``text:`` in ``props``, so interpolate
    the variable there yourself -- ``f"text:{speed};list:Slow,Medium,Fast;"`` --
    or set it afterwards with ``.value``.

    Args:
        props (str): Semicolon-separated properties. The options go in ``list:``
            (comma separated) and the closed-state label in ``text:``, e.g.
            ``"text:Red;list:Red,Green,Blue"``. NOT ``items:`` - a dropdown with no
            ``list:`` has nothing to render and the engine dies allocating for it
            (``MemoryError: bad allocation``), which reads as anything but a typo.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to write the selection to when it
            changes. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.

    Returns:
        Dropdown: The layout item created.

    Example:
        speed = gui_drop_down("text:Medium;list:Slow,Medium,Fast;", var="speed_setting")
        speed.value = "Fast"      # move the selection from script
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
