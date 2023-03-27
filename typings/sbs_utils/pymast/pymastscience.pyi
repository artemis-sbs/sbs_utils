from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.pymast.pollresults import PollResults
class PyMastScience(object):
    """class PyMastScience"""
    def __init__ (self, task, player_id, npc_id_or_filter, scans) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def message (self, sim, message, player_id, event):
        ...
    def run (self):
        ...
    def selected (self, sim, player_id, event):
        ...
