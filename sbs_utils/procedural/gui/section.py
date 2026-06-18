from ...helpers import FrameContext
from ..style import apply_control_styles
from .update import gui_represent

def gui_section(style=None):
    """Create a top-level GUI layout section at a specific screen area.

    Sections are the primary way to position content on screen. The ``area``
    style property sets the region (left, top, right, bottom as percentages).
    Content added after this call is placed inside the section until the next
    ``gui_section`` or the frame ends.

    Args:
        style (str, optional): CSS-like style string. Use ``area:`` to position
            the section, e.g. ``"area:10,10,90,90;"``. Defaults to None.

    Returns:
        Layout: The layout object for this section.

    Example:
        gui_section(style="area:5,5,95,50;")
        gui_text("Top half of screen")
        gui_section(style="area:5,50,95,95;")
        gui_text("Bottom half of screen")
    """

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    
    page.add_section()
    layout_item = page.get_pending_layout() 
    apply_control_styles(".section", style, layout_item, task)
    return layout_item

class PageSubSection:
    def __init__(self, style) -> None:
        page = FrameContext.page
        self.sub_section = None
        if page is None:
            return None
        self.page = page
        self.style = style
        self.add = True

    @property
    def tag(self):
        if self.sub_section is not None:
            return self.sub_section.tag
        return None
    
    @property
    def click_tag(self):
        if self.sub_section is not None:
            return self.sub_section.click_tag
        return None
    
    @click_tag.setter
    def click_tag(self, v):
        if self.sub_section is not None:
            self.sub_section.click_tag = v
    
    def is_message_for(self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object

        Args:
            event (EVENT): the engine event

        Returns:
            bool: if the gui_message MessageTrigger should be True
        """
        return event.sub_tag == self.sub_section.tag or event.sub_tag == self.sub_section.click_tag
  

    def __enter__(self):
        # Allow reentering
        self.sub_section = self.page.push_sub_section(self.style, self.sub_section, False)
        

    # Pythons expects 4 args, mast only 1
    # Python's are exception related
    def __exit__(self, ex=None, value=None, tb=None):
        self.page.pop_sub_section(self.add, False)
        self.add = False
        if ex:
            return False
        return True

    def represent(self, event):
        self.sub_section.represent(event)


def gui_sub_section(style=None):
    """Create a nested layout sub-section, used as a context manager.

    Sub-sections let you group and style a subset of content within the current
    section. Use with Python's ``with`` statement in MAST via the ``with``
    keyword. The sub-section is added to the current layout when the ``with``
    block exits.

    Args:
        style (str, optional): CSS-like style string controlling the column
            width, row height, background, etc. of the sub-section.
            Defaults to None.

    Returns:
        PageSubSection: Context manager object. Use with ``with``.

    Example:
        gui_row(style="row-height:3em;")
        with gui_sub_section(style="col-width:30%;"):
            gui_text("Left column")
        with gui_sub_section():
            gui_text("Right column")
    """
    return PageSubSection(style)

from ...pages.layout.layout import RegionType
class PageRegion:
    def __init__(self, style) -> None:
        page = FrameContext.page
        if page is None:
            return None
        self.page = page
        self.style = style
        self.sub_section = None
        # Create  top level layout        
        self.sub_section  = gui_section(style)
 
    @property
    def tag(self):
        if self.sub_section is not None:
            return self.sub_section.tag
        return None
    
    @property
    def click_tag(self):
        if self.sub_section is not None:
            return self.sub_section.click_tag
        return None      

    def __enter__(self):
        # Allow reentering
        self.sub_section = self.page.push_sub_section(self.style, self.sub_section, self.sub_section.region)
        self.sub_section.region_type = RegionType.REGION_ABSOLUTE
        

    # Pythons expects 4 args, mast only 1
    # Python's are exception related
    def __exit__(self, ex=None, value=None, tb=None):
        self.page.pop_sub_section(False, self.sub_section.region)
        if self.sub_section.region:
            gui_represent(self.sub_section)

    def show(self, _show):
        self.sub_section.show(_show)
        # Avoid cascade?
        self.sub_section.mark_visual_dirty()

    def rebuild(self):
        self.sub_section.rebuild()
        return self

    @property
    def is_hidden(self):
        return self.sub_section.is_hidden

    def represent(self, e):
        self.sub_section.represent(e)




def gui_region(style=None):
    """Create a re-representable GUI region pinned to an absolute screen area.

    Unlike ``gui_sub_section``, a region uses absolute positioning (the ``area``
    style property) and can be redrawn independently with ``region.represent()``.
    Use it for UI panels that update without redrawing the entire page.
    Also a context manager — content inside the ``with`` block is placed in
    the region.

    Args:
        style (str, optional): CSS-like style string. The ``area:`` property
            sets the absolute screen position (left, top, right, bottom %).
            Defaults to None.

    Returns:
        PageRegion: Context manager object with ``show()``, ``rebuild()``,
            and ``represent()`` methods.

    Example:
        hud = gui_region(style="area:0,0,100,10;")
        with hud:
            gui_text("HUD content here")
        ~~ hud.represent(event) ~~   # refresh just this region later
    """
    return PageRegion(style)

