from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.gui_control import GuiControl
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply style information to a layout item based on the type of the layout, and apply the extra styles as needed.
    Args:
        control_name (str): The name of the control style.
        extra_style (str): A CSS-style string containing extra style definitions which override those in the control style.
        layout_item (LayoutItem): The layout item for which the style is to be applied."""
def gui_content (content, style=None, var=None):
    """Place a python code widget e.g. list box using the layout system
    
    Args:
        content (widget): A gui widget code in python
        style (str, optional): Style. Defaults to None.
        var (str, optional): The variable to set the widget's value to. Defaults to None.
    
    Returns:
        layout object: The layout object"""
