from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.radio_button_group import RadioButtonGroup
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_radio (msg, style=None, var=None, data=None, vertical=False):
    """Draw a radio button list
    
    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        vertical (bool): Layout vertical if True, default False means horizontal
    
    Returns:
        layout object: The Layout object created"""
def gui_vradio (msg, style=None, var=None, data=None):
    """Draw a vertical radio button list
    
    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
