from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.radio_button import RadioButton
from sbs_utils.pages.layout.row import Row
class RadioButtonGroup(Column):
    """class RadioButtonGroup"""
    def __init__ (self, tag, buttons, value, vertical) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def is_message_for (self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object
        
        Args:
            event (EVENT): the engine event
        
        Returns:
            bool: if the gui_message MessageTrigger should be True"""
    def on_message (self, event):
        ...
    @property
    def selected_index (self):
        ...
    @selected_index.setter
    def selected_index (self, v):
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
