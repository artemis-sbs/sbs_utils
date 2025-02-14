from ...helpers import FrameContext
from ..style import apply_control_styles
from .update import gui_represent

def gui_section(style=None):
    """ Create a new gui section that uses the area specified in the style

    Args:
        style (style, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
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

    def __enter__(self):
        # Allow reentering
        self.sub_section = self.page.push_sub_section(self.style, self.sub_section, False)
        

    # Pythons expects 4 args, mast only 1
    # Python's are exception related
    def __exit__(self, ex=None, value=None, tb=None):
        self.page.pop_sub_section(self.add, False)
        self.add = False


def gui_sub_section(style=None):
    """ Create a new gui section that uses the area specified in the style

    Args:
        style (style, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
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

    def rebuild(self):
        self.sub_section.rebuild()
        return self

    @property
    def is_hidden(self):
        return self.sub_section.is_hidden

    def represent(self, e):
        self.sub_section.represent(e)




def gui_region(style=None):
    """ Create a new gui section that uses the area specified in the style

    Args:
        style (style, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    return PageRegion(style)

