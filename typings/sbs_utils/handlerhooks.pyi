from sbs_utils.agent import Agent
from sbs_utils.extra_dispatcher import ClientStringDispatcher
from sbs_utils.extra_dispatcher import HotkeyDispatcher
from sbs_utils.damagedispatcher import CollisionDispatcher
from sbs_utils.damagedispatcher import DamageDispatcher
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import Context
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def cosmos_event_handler (sim, event):
    ...
def format_exception (message, source):
    ...
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_mission_name ():
    """Get the name of the current mission.
    
    Returns the name derived from the script directory basename.
    Cached after first call.
    
    Returns:
        str: The mission folder name."""
def get_startup_mission_name ():
    """Get the default mission name from preferences.
    
    Returns:
        str: The default mission folder name from game preferences."""
def print_event (event):
    """Print the event data.
    Args:
        event (event): The event of interest."""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def tick_the_rest (event):
    ...
class ErrorPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self, msg) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def present (self, event):
        """present
        
        Called to have the page create and update the gui content it is presenting"""
