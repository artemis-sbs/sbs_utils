from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.text_input import TextInput
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_input (props, style=None, var=None, data=None):
    """Draw a text type in
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
