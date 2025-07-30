from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout.text_area import TextArea
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_text (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def gui_text_area (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def text_sanitize (text):
    ...
