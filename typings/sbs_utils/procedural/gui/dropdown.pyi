from sbs_utils.pages.layout.dropdown import Dropdown
from sbs_utils.helpers import FrameContext
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
def gui_drop_down (props, style=None, var=None, data=None):
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
        speed.value = "Fast"      # move the selection from script"""
