from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Trigger
def gui_message (layout_item, label=None):
    """Trigger to watch when the specified layout element has a message
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached"""
def gui_message_callback (layout_item, cb):
    """Trigger to watch when the specified layout element has a message
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached"""
def gui_message_label (layout_item, label):
    ...
class MessageTrigger(Trigger):
    """class MessageTrigger"""
    def __init__ (self, task, layout_item, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
