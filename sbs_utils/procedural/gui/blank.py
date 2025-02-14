"""
This module exposes the gui_blank function

The gui_blank function is used to insert a black space in a layout.
Blanks are useful to add space.

Example:
    To insert a blank part of the layout just call gui_blank::

        gui_blank()

    Proving a count will allow inserting multiple blanks::

        gui_blank(4)

    One use of blanks it to help center an element but also adding space::

        gui_blank()
        gui_icon(...)
        gui_blank()
"""
from ...helpers import FrameContext
from ..style import apply_control_styles


from ...pages.layout.blank import Blank
def gui_blank(count=1, style=None):
    """adds an empty column to the current gui ow

    Args:
        style (_type_, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    for _ in range(count):
        layout_item = Blank()
        apply_control_styles(".blank", style, layout_item, task)
        # Last in case tag changed in style
        page.add_content(layout_item, None)
    return layout_item
