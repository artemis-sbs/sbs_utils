from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast import Mast
def signal_emit (name, data=None):
    ...
def signal_register (name, label, server=False, task=None, loc=0, is_jump=True):
    ...
class SignalLabelInfo(object):
    """class SignalLabelInfo"""
    def __init__ (self, is_jump, label, loc, server) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
