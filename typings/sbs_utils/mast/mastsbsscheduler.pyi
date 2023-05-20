from sbs_utils.mast.mastsbs import Broadcast
from sbs_utils.mast.mastsbs import Button
from sbs_utils.mast.mastsbs import Comms
from sbs_utils.mast.mastsbs import Load
from sbs_utils.mast.mastsbs import Route
from sbs_utils.mast.mastsbs import ScanResult
from sbs_utils.mast.mastsbs import ScanTab
from sbs_utils.mast.mastsbs import Simulation
from sbs_utils.mast.mastsbs import Tell
from sbs_utils.mast.mastsbs import TransmitReceive
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.damagedispatcher import DamageDispatcher
from sbs_utils.mast.errorpage import ErrorPage
from sbs_utils.mast.mastobjects import GridObject
from sbs_utils.mast.mastobjects import MastSpaceObject
from sbs_utils.mast.mastobjects import Npc
from sbs_utils.mast.mastobjects import PlayerShip
from sbs_utils.mast.mastobjects import Terrain
from sbs_utils.gui import Gui
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import Scope
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastRuntimeNode
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.mastscheduler import PollResults
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from functools import partial
def func(*argv):
    """assign_client_to_ship(arg0: int, arg1: int) -> None
    
    Tells a client computer which ship it should control."""
def handle_purge_tasks (ctx, so):
    """This will clear out all tasks related to the destroyed item"""
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
class CommsInfoRuntimeNode(MastRuntimeNode):
    """class CommsInfoRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
class CommsRuntimeNode(MastRuntimeNode):
    """class CommsRuntimeNode"""
    def clear (self):
        ...
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
    def set_buttons (self, origin_id, selected_id):
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
    def grid_spawn (self, id, name, tag, x, y, icon, color, roles):
        ...
    def npc_spawn (self, x, y, z, name, side, art_id, behave_id):
        ...
    def player_spawn (self, x, y, z, name, side, art_id):
        ...
    def run (self, ctx, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def sbs_tick_tasks (self, ctx):
        ...
    def terrain_spawn (self, x, y, z, name, side, art_id, behave_id):
        ...
class RegexEqual(str):
    """str(object='') -> str
    str(bytes_or_buffer[, encoding[, errors]]) -> str
    
    Create a new string object from the given object. If encoding or
    errors is specified, then the object must expose a data buffer
    that will be decoded using the given encoding and error handler.
    Otherwise, returns the result of object.__str__() (if defined)
    or repr(object).
    encoding defaults to sys.getdefaultencoding().
    errors defaults to 'strict'."""
    def __eq__ (self, pattern):
        """Return self==value."""
class RouteRuntimeNode(MastRuntimeNode):
    """class RouteRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Route):
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
    def science_selected (self, ctx, an_id, event):
        ...
    def start_scan (self, sim, origin_id, selected_id, extra_tag):
        ...
class SimulationRuntimeNode(MastRuntimeNode):
    """class SimulationRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Simulation):
        ...
class TellRuntimeNode(MastRuntimeNode):
    """class TellRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Tell):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Tell):
        ...
class TransmitReceiveRuntimeNode(MastRuntimeNode):
    """class TransmitReceiveRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.TransmitReceive):
        ...
