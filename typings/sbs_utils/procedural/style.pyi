from sbs_utils.mast.parsers import StyleDefinition
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply style information to a layout item based on the type of the layout, and apply the extra styles as needed.
    Args:
        control_name (str): The name of the control style.
        extra_style (str): A CSS-style string containing extra style definitions which override those in the control style.
        layout_item (LayoutItem): The layout item for which the style is to be applied."""
def apply_style_def (style_def, layout_item, task):
    """Apply the style information to the layout item.
    Args:
        style_def (dict): The style definition data.
        layout_item (LayoutItem): The layout item to which the style information is to be applied.
        task (MastAsyncTask): The task on which to apply the style. Should be a GUI task."""
def apply_style_name (style_name, layout_item, task):
    """Apply the predefined style infomormation for the style name to the layout item.
    Args:
        style_name (str): The name of the style.
        layout_item (LayoutItem): The layout item to which the style information is to be applied.
        task (MastAsyncTask): The task on which to apply the style. Should be a GUI task."""
def compile_formatted_string (message):
    """Build a compiled version of the format string for faster execution.
    
    Args:
        message (str): The format string
    
    Returns:
        CodeType: compiled python eval"""
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
