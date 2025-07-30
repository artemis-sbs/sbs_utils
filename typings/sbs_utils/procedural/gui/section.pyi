from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.layout import RegionType
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_region (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_represent (layout_item):
    """redraw an item
    
    ??? Note
        For sections it will recalculate the layout and redraw all items
    
    Args:
        layout_item (layout_item): """
def gui_section (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_sub_section (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
class PageRegion(object):
    """class PageRegion"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex=None, value=None, tb=None):
        ...
    def __init__ (self, style) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def is_hidden (self):
        ...
    def rebuild (self):
        ...
    def represent (self, e):
        ...
    def show (self, _show):
        ...
class PageSubSection(object):
    """class PageSubSection"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex=None, value=None, tb=None):
        ...
    def __init__ (self, style) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def represent (self, event):
        ...
