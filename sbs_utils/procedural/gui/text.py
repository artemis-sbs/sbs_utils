from ...helpers import FrameContext
from ..style import apply_control_styles

from ...pages.layout.text import Text
from ...pages.layout.text_area import TextArea

def gui_text(props, style=None):
    """ Add a gui text object

    valid properties 
        text
        color
        font


    props (str): property string 
    style (style, optional): The style
    """
    page = FrameContext.page
    task = FrameContext.task

    if page is None:
        return
    if style is None: 
        style = ""
    else:
        style = task.compile_and_format_string(style)

    props = task.compile_and_format_string(props)
    
    layout_item = Text(page.get_tag(), props)
    apply_control_styles(".text", style, layout_item, task)

    page.add_content(layout_item, None)
    return layout_item


def text_sanitize(text):
    # text = text.replace(",", "_")
    #text = text.replace(":", "_")
    return text

def gui_text_area(props, style=None):
    """ Add a gui text object

    valid properties 
        text
        color
        font


    props (str): property string 
    style (style, optional): The style
    """
    page = FrameContext.page
    task = FrameContext.task

    props = task.compile_and_format_string(props)

    if page is None:
        return
    if style is None: 
        style = ""
    else:
        style = task.compile_and_format_string(style)

    layout_item = TextArea(page.get_tag(), text_sanitize(props))
    apply_control_styles(".textarea", style, layout_item, task)

    page.add_content(layout_item, None)
    return layout_item
