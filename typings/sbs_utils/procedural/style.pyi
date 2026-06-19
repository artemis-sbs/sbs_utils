from sbs_utils.mast.parsers import StyleDefinition
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
def apply_style_def (style_def, layout_item, task):
    """Apply a style definition dict directly to a layout item.
    
    Handles ``area``, ``orientation``, ``row-height``, ``col-width``,
    ``margin``, ``border``, ``padding``, ``color``, ``font``, ``justify``,
    ``background``, ``background-color``, ``background-image``,
    ``border-image``, ``border-color``, ``click_*``, and ``tag`` keys.
    
    Args:
        style_def (dict): Parsed style definition (key → value).
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def apply_style_name (style_name, layout_item, task):
    """Look up a named style definition and apply it to a layout item.
    
    Args:
        style_name (str): Name of the style to apply.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def compile_formatted_string (message):
    """Compile a format string into a Python code object for faster repeated evaluation.
    
    Strings containing ``{`` are wrapped in an f-string and compiled with
    ``eval`` mode. Strings without ``{`` are returned unchanged.
    
    Args:
        message (str): The format string, optionally containing ``{var}``
            placeholders.
    
    Returns:
        CodeType | str | None: A compiled code object if the string contains
            ``{``, the original string otherwise, or ``None`` if ``message``
            is ``None``."""
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
