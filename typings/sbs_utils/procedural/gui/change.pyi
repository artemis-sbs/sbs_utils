from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Trigger
def gui_change (code, label):
    """Register a per-tick change watch on a Python expression.
    
    Evaluates ``code`` each tick and executes ``label`` when its value differs
    from the previous tick. Python equivalent of the MAST ``on change``
    construct. The trigger is attached to the current task and runs for as long
    as the task is active.
    
    Args:
        code (str): Python expression to evaluate each tick, e.g.
            ``"ship_speed > 100"``.
        label: MAST label or inline block to execute when the value changes.
    
    Example:
        gui_change("shield_level", shield_warning)
        ///shield_warning
            gui_text("Shields changed!")"""
class ChangeTrigger(Trigger):
    """class ChangeTrigger"""
    def __init__ (self, task, node, label=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def run (self):
        ...
    def test (self):
        ...
