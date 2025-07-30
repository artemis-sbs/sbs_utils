from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.gui_control import GuiControl
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_content (content, style=None, var=None):
    """Place a python code widget e.g. list box using the layout system
    
    Args:
        content (widget): A gui widget code in python
        style (str, optional): Style. Defaults to None.
        var (str, optional): The variable to set the widget's value to. Defaults to None.
    
    Returns:
        layout object: The layout object"""
