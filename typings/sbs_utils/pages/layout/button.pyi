from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
class Button(Column):
    """class Button"""
    def __init__ (self, tag, message) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def update (self, message):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
