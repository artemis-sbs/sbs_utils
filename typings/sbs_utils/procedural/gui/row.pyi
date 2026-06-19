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
def gui_row (style=None):
    """Start a new layout row, pushing subsequent items to the next line.
    
    Call before adding items that should appear on a fresh row. Without
    explicit rows, items flow left-to-right across the current row.
    
    Args:
        style (str, optional): CSS-like style overrides for the row container.
            Defaults to None.
    
    Returns:
        Row: The row layout object.
    
    Example:
        gui_text("Name:")
        gui_row()
        gui_input("", var="ship_name")"""
