from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
class IconButton(Column):
    """class IconButton"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def update (self, props):
        """Same contract as `Icon.update`: change the look AND say so, or the new
        look sits in the object waiting for a rebuild that may never come."""
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
