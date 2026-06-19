from sbs_utils.mast.parsers import StyleDefinition
def gui_set_style_def (name, style):
    """Parse a style string and register it under a named class.
    
    After registering, the name can be used as a CSS class reference in any
    style string (e.g. ``".my_style"``).
    
    Args:
        name (str): Class name to register (conventionally prefixed with
            ``"."``), e.g. ``".alert"``.
        style (str): CSS-like style string to associate with the name.
    
    Returns:
        StyleDefinition: The parsed and registered style object.
    
    Example:
        gui_set_style_def(".alert", "color:red;background:#400;")
        gui_text("Warning!", style=".alert")"""
def gui_style_def (style):
    """Parse a CSS-like style string into a StyleDefinition object.
    
    Useful when you want to pre-parse a style string and inspect or reuse
    it without re-parsing each time.
    
    Args:
        style (str): CSS-like style string, e.g. ``"color:red;col-width:50%;"``.
    
    Returns:
        StyleDefinition: Parsed style object.
    
    Example:
        s = gui_style_def("color:green;font:hud_font;")"""
