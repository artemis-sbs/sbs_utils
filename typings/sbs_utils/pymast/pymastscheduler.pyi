from sbs_utils.pymast.pymasttask import DataHolder
from sbs_utils.pymast.pymasttask import PyMastTask
from sbs_utils.pymast.pollresults import PollResults
class PyMastScheduler(object):
    """class PyMastScheduler"""
    def __init__ (self, story, label) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def schedule_a_task (self, task):
        ...
    def schedule_task (self, label):
        ...
    def tick (self, sim):
        ...
