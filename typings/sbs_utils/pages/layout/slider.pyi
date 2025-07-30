from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
class Slider(Column):
    """class Slider"""
    def __init__ (self, tag, value, props, is_int=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def on_message (self, event):
        ...
    def update (self, props):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
