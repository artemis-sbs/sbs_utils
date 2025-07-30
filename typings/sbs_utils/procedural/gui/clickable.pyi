from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import Scope
from sbs_utils.futures import Trigger
def gui_click (name_or_layout_item=None, label=None):
    """Trigger to watch when the specified layout element is clicked
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the element is clicked"""
class ClickableTrigger(Trigger):
    """class ClickableTrigger"""
    def __init__ (self, task, name, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def click (self, click_tag):
        ...
