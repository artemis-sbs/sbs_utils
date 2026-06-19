from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.text_input import TextInput
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
def gui_input (props, style=None, var=None, data=None):
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
        gui_input("", var="ship_name", style="col-width:50%;")"""
