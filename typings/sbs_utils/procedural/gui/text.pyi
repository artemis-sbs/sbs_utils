from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout.text_area import TextArea
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
def gui_text (props, style=None):
    """Add a text label to the current GUI layout.
    
    Args:
        props (str): Text content or property string, e.g. ``"Hello"`` or
            ``"$text:Hello;color:white;"``. Supports ``{var}`` interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Text: The layout item created.
    
    Example:
        gui_text("Hull: {hull_pct}%")
        gui_text("$text:WARNING;color:red;")"""
def gui_text_area (props, style=None):
    """Add a rich text area to the current GUI layout.
    
    Supports Markdown-style formatting and inline image references
    (``![](image://key)``). Use for multi-line or formatted text blocks.
    
    Args:
        props (str): Text content or Markdown string. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        TextArea: The layout item created.
    
    Example:
        gui_text_area("## Status\nAll systems nominal.")
        gui_text_area("![](image://logo?scale=0.5) Mission active")"""
def text_sanitize (text):
    ...
