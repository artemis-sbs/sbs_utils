from sbs_utils.mast.mastsbs import Broadcast
from sbs_utils.mast.mastsbs import Button
from sbs_utils.mast.mastsbs import Comms
from sbs_utils.mast.mastsbs import FollowRoute
from sbs_utils.mast.mastsbs import Route
from sbs_utils.mast.mastsbs import Scan
from sbs_utils.mast.mastsbs import ScanResult
from sbs_utils.mast.mastsbs import ScanTab
from sbs_utils.mast.mastsbs import Simulation
from sbs_utils.mast.mastsbs import TransmitReceive
from sbs_utils.mast.mastscheduler import ChangeRuntimeNode
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastRuntimeNode
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.mastscheduler import PollResults
from sbs_utils.damagedispatcher import CollisionDispatcher
from sbs_utils.damagedispatcher import DamageDispatcher
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.mast.errorpage import ErrorPage
from sbs_utils.helpers import FakeEvent
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.gui import Gui
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import Scope
from sbs_utils.mast.mastobjects import MastSpaceObject
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from functools import partial
def func(*argv):
    """assign_client_to_ship(arg0: int, arg1: int) -> None
    
    Tells a client computer which ship it should control."""
def handle_purge_tasks (so):
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
    def comms_message (self, message, an_id, event):
        ...
    def comms_selected (self, an_id, event):
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
class FollowRouteRuntimeNode(MastRuntimeNode):
    """class FollowRouteRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.FollowRoute):
        ...
class MastSbsScheduler(MastScheduler):
    """class MastSbsScheduler"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def get_seconds (self, clock):
        """Gets time for a given clock default is just system """
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def resolve_id (other: 'EngineObject | CloseData | int'):
        ...
    def resolve_py_object (other: 'EngineObject | CloseData | int'):
        ...
    def run (self, ctx, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def sbs_tick_tasks (self, ctx):
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
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Scan):
        ...
    def expand (self, button: sbs_utils.mast.mastsbs.ScanTab, task: sbs_utils.mast.mastscheduler.MastAsyncTask):
        ...
    def leave (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Comms):
        ...
    def science_message (self, message, an_id, event):
        ...
    def science_selected (self, an_id, event):
        ...
    def start_scan (self, origin_id, selected_id, extra_tag):
        ...
class SimulationRuntimeNode(MastRuntimeNode):
    """class SimulationRuntimeNode"""
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.Simulation):
        ...
class TransmitReceiveRuntimeNode(MastRuntimeNode):
    """class TransmitReceiveRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.mastsbs.TransmitReceive):
        ...
