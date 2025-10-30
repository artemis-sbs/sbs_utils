from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast import Mast
def signal_emit (name, data=None):
    """Emit a signal to trigger all instances of the signal route to run.
    Args:
        name (str): The name of the signal.
        data (dict): The data to provide to the signal route."""
def signal_register (name, label, server=False, task=None, loc=0, is_jump=True):
    """Register a new signal route, linking the signal name with the specified label.
    Args:
        name (str): The name of the signal.
        label (str | Label): The label to run when the signal is emitted.
        server (bool, optional): Should the label run only for the server (as a shared signal)? Default is False.
        loc (int, optional): The index of the sublabel to run. Default is 0.
        is_jump (bool, optional): Should the signal trigger a jump to the signal's label, continuing the current task? Default is True."""
class SignalLabelInfo(object):
    """class SignalLabelInfo"""
    def __init__ (self, is_jump, label, loc, server) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
