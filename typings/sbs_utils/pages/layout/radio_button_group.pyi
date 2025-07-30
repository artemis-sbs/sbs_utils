from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.radio_button import RadioButton
from sbs_utils.pages.layout.row import Row
class RadioButtonGroup(Column):
    """class RadioButtonGroup"""
    def __init__ (self, tag, buttons, value, vertical) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def on_message (self, event):
        ...
    def set_bounds (self, bounds) -> None:
        ...
    def update (self, props):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
