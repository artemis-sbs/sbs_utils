from sbs_utils.pages.layout.button import Button
from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Promise
def apply_control_styles (control_name, extra_style, layout_item, task):
    ...
def gui_button (props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a gui button
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
        data (object): The data to pass to the button's label
        on_press (label, callable, Promise): Handle a button press, label is jumped to, callable is called, Promise has results set
    
    Returns:
        layout object: The Layout object created"""
class ButtonResult(object):
    """class ButtonResult"""
    def __init__ (self, layout_item, client_id):
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def data (self):
        ...
    @property
    def value (self):
        ...
class MessageHandler(object):
    """class MessageHandler"""
    def __init__ (self, layout_item, task, handler, is_sub_task) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
