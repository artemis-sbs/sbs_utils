from sbs_utils.pages.layout.face import Face
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
def gui_face (face, style=None):
    """Add a character face portrait to the current GUI layout.
    
    Renders the named face asset, typically used in comms panels to show the
    speaker's portrait.
    
    Args:
        face (str): Face asset name or property string, e.g. ``"crew/captain"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Face: The layout item created.
    
    Example:
        gui_face("crew/captain")"""
