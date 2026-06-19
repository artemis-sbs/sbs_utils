from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.layout import RegionType
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
def gui_region (style=None):
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
        ~~ hud.represent(event) ~~   # refresh just this region later"""
def gui_represent (layout_item):
    """Redraw a layout item on the client screen.
    
    For sections and regions, recalculates the entire sub-layout and redraws
    all children. For individual items or rows, redraws that element only.
    
    Args:
        layout_item: The layout object to redraw.
    
    Example:
        gui_represent(my_section)"""
def gui_section (style=None):
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
        gui_text("Bottom half of screen")"""
def gui_sub_section (style=None):
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
            gui_text("Right column")"""
class PageRegion(object):
    """class PageRegion"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex=None, value=None, tb=None):
        ...
    def __init__ (self, style) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def click_tag (self):
        ...
    @property
    def is_hidden (self):
        ...
    def rebuild (self):
        ...
    def represent (self, e):
        ...
    def show (self, _show):
        ...
    @property
    def tag (self):
        ...
class PageSubSection(object):
    """class PageSubSection"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex=None, value=None, tb=None):
        ...
    def __init__ (self, style) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def click_tag (self):
        ...
    @click_tag.setter
    def click_tag (self, v):
        ...
    def is_message_for (self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object
        
        Args:
            event (EVENT): the engine event
        
        Returns:
            bool: if the gui_message MessageTrigger should be True"""
    def represent (self, event):
        ...
    @property
    def tag (self):
        ...
