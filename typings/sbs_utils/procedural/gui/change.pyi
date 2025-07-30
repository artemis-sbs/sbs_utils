from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Trigger
def gui_change (code, label):
    """Trigger to watch when the specified value changes
    This is the python version of the mast on change construct
    
    Args:
        code (str): Code to evaluate
        label (label): The label to jump to run when the value changes
    
    Returns:
        trigger: A trigger watches something and runs something when the element is clicked"""
class ChangeTrigger(Trigger):
    """class ChangeTrigger"""
    def __init__ (self, task, node, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def run (self):
        ...
    def test (self):
        ...
