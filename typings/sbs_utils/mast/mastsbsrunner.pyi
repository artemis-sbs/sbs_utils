from sbs_utils.mast.mastsbs import Button
from sbs_utils.mast.mastsbs import Comms
from sbs_utils.mast.mastsbs import Near
from sbs_utils.mast.mastsbs import Simulation
from sbs_utils.mast.mastsbs import Target
from sbs_utils.mast.mastsbs import Tell
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.mast.errorpage import ErrorPage
from sbs_utils.gui import Gui
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastrunner import MastAsync
from sbs_utils.mast.mastrunner import MastRunner
from sbs_utils.mast.mastrunner import MastRuntimeNode
from sbs_utils.mast.mastrunner import PollResults
from sbs_utils.spaceobject import SpaceObject
class ButtonRunner(MastRuntimeNode):
    """class ButtonRunner"""
    def poll (self, mast, runner, node):
        ...
class CommsRunner(MastRuntimeNode):
    """class CommsRunner"""
    def comms_message (self, sim, message, an_id, event):
        ...
    def comms_selected (self, sim, an_id, event):
        ...
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def leave (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def set_buttons (self, from_id, to_id):
        ...
class MastSbsRunner(MastRunner):
    """class MastSbsRunner"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def run (self, sim, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def sbs_tick_threads (self, sim):
        ...
class NearRunner(MastRuntimeNode):
    """class NearRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Near):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Near):
        ...
class SimulationRunner(MastRuntimeNode):
    """class SimulationRunner"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Simulation):
        ...
class TargetRunner(MastRuntimeNode):
    """class TargetRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Target):
        ...
    def poll (self, mast, thread, node: sbs_utils.mast.mastsbs.Target):
        ...
class TellRunner(MastRuntimeNode):
    """class TellRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Tell):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Tell):
        ...
