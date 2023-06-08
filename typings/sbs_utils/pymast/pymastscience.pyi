from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.pymast.pollresults import PollResults
class PyMastScience(object):
    """class PyMastScience"""
    def __init__ (self, task, scans, origin_id, selected_id) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def handle_selected (self, sim, origin_id, selected_id, scan_type):
        ...
    def message (self, ctx, message, player_id, event):
        ...
    def run (self):
        ...
    def selected (self, ctx, origin_id, event):
        ...
