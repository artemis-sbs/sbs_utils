from sbs_utils.mast.mastsbs import Broadcast
from sbs_utils.mast.mastsbs import Button
from sbs_utils.mast.mastsbs import ButtonSet
from sbs_utils.mast.mastsbs import Comms
from sbs_utils.mast.mastsbs import Load
from sbs_utils.mast.mastsbs import Near
from sbs_utils.mast.mastsbs import Role
from sbs_utils.mast.mastsbs import ScanResult
from sbs_utils.mast.mastsbs import ScanTab
from sbs_utils.mast.mastsbs import Simulation
from sbs_utils.mast.mastsbs import Target
from sbs_utils.mast.mastsbs import Tell
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.mast.errorpage import ErrorPage
from sbs_utils.gui import Gui
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import Scope
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastRuntimeNode
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.mastscheduler import PollResults
from sbs_utils.mast.mastobjects import MastSpaceObject
from sbs_utils.mast.mastobjects import Npc
from sbs_utils.mast.mastobjects import PlayerShip
from sbs_utils.mast.mastobjects import Terrain
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
def func(*argv):
    """assign_client_to_ship(arg0: int, arg1: int) -> None
    
    Tells a client computer which ship it should control."""
class BroadcastRuntimeNode(MastRuntimeNode):
    """class BroadcastRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Broadcast):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Broadcast):
        ...
class ButtonRuntimeNode(MastRuntimeNode):
    """class ButtonRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Button):
        ...
class ButtonSetRuntimeNode(MastRuntimeNode):
    """class ButtonSetRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.ButtonSet):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.ButtonSet):
        ...
class CommsRuntimeNode(MastRuntimeNode):
    """class CommsRuntimeNode"""
    def comms_message (self, sim, message, an_id, event):
        ...
    def comms_selected (self, sim, an_id, event):
        ...
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def expand (self, button: sbs_utils.mast.mastsbs.Button, task: sbs_utils.mast.mastscheduler.MastAsyncTask):
        ...
    def leave (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def set_buttons (self, from_id, to_id):
        ...
class LoadRuntimeNode(MastRuntimeNode):
    """class LoadRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Load):
        ...
    def process_data (self, content):
        ...
class MastSbsScheduler(MastScheduler):
    """class MastSbsScheduler"""
    def Npc (self):
        ...
    def PlayerShip (self):
        ...
    def Terrain (self):
        ...
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def get_seconds (self, clock):
        """Gets time for a given clock default is just system """
    def npc_spawn (self, x, y, z, name, side, art_id, behave_id):
        ...
    def player_spawn (self, x, y, z, name, side, art_id):
        ...
    def run (self, sim, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def sbs_tick_tasks (self, sim):
        ...
    def terrain_spawn (self, x, y, z, name, side, art_id, behave_id):
        ...
class NearRuntimeNode(MastRuntimeNode):
    """class NearRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Near):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Near):
        ...
class RoleRuntimeNode(MastRuntimeNode):
    """class RoleRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Role):
        ...
class ScanResultRuntimeNode(MastRuntimeNode):
    """class ScanResultRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.ScanResult):
        ...
class ScanRuntimeNode(MastRuntimeNode):
    """class ScanRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def expand (self, button: sbs_utils.mast.mastsbs.ScanTab, task: sbs_utils.mast.mastscheduler.MastAsyncTask):
        ...
    def leave (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def science_message (self, sim, message, an_id, event):
        ...
    def science_selected (self, sim, an_id, event):
        ...
class SimulationRuntimeNode(MastRuntimeNode):
    """class SimulationRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Simulation):
        ...
class TargetRuntimeNode(MastRuntimeNode):
    """class TargetRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Target):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.mastsbs.Target):
        ...
class TellRuntimeNode(MastRuntimeNode):
    """class TellRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Tell):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Tell):
        ...
