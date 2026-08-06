from sbs_utils.agent import Agent
from sbs_utils.extra_dispatcher import ClientStringDispatcher
from sbs_utils.extra_dispatcher import HotkeyDispatcher
from sbs_utils.damagedispatcher import CollisionDispatcher
from sbs_utils.damagedispatcher import DamageDispatcher
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import Context
from sbs_utils.helpers import FrameContext
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.launchdispatcher import LaunchDispatcher
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def _cosmos_event_handler (sim, event):
    ...
def _phase (store, name, fn, *args):
    """Time one phase of the event handler into `store` (name -> seconds).
    
    Used only to enrich the existing >33ms "Elapsed time" spike print with a
    per-phase breakdown (dispatch_tick / spawn / Gui.present / gc / dirty /
    delete), so a spike can be attributed to a subsystem live in the engine.
    Cost is one perf_counter pair per phase (~sub-microsecond); the breakdown is
    only printed on a frame that already exceeds the spike threshold."""
def _probe_agents () -> int:
    ...
def _report_reentry (event):
    ...
def amd_cutscene_clear ():
    """Drop every loaded cutscene/rundown/cast - the per-mission reset."""
def amd_declared_addons_clear ():
    """Drop the cached addon list - the per-mission reset."""
def clear_shared ():
    ...
def cosmos_event_handler (sim, event):
    """Engine entry point. Guards the non-reentrancy the rest of this file assumes."""
def fleet_tables_count ():
    """Reset-ledger probe."""
def format_exception (message, source):
    ...
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
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
def grid_data_is_loaded () -> int:
    """Reset-ledger probe: 1 while grid data (possibly mod-merged) is held, else 0."""
def grid_theme_current_index () -> int:
    """Reset-ledger probe: the selected theme index, which must be back to 0 (default).
    
    Not a container - a setting. A mission that selected theme 1 would silently hand it
    to the next mission, which is a whole game re-skinned for no reason anyone could see."""
def grid_theme_is_loaded () -> int:
    """Reset-ledger probe: 1 while theme data is held, else 0."""
def landmarks_registry_clear ():
    """Drop the declared-record registry - the per-mission reset."""
def lore_clear ():
    """Drop every registered source - the per-mission reset."""
def lore_sources ():
    """Registered sources, in registration order."""
def print_event (event):
    """Print the event data.
    Args:
        event (event): The event of interest."""
def register_reset_state (name: str, probe) -> None:
    """Declare a per-mission container that must be empty after reset_mission_state().
    
    `probe` returns its current size (an int). Registration is idempotent by name, so
    re-importing a module does not duplicate it."""
def reset_mission_audit () -> dict:
    """Sizes of every registered container. Non-zero entries after a reset are leaks.
    
    Returns {name: size} for the NON-EMPTY ones only - an empty dict means clean."""
def reset_mission_state ():
    """Reset all per-mission runtime state for a fresh mission / in-process recompile."""
def rundown_clear ():
    """Empty the rundown and both desks."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def ship_data_is_loaded () -> int:
    """Reset-ledger probe: 1 while ship data (possibly mod-merged) is held, else 0."""
def ship_data_pending_count ():
    """How many mod-contributed entries are waiting to be written. Reset-ledger probe."""
def terrain_sow_pending ():
    """How many queued units of terrain work are still to run."""
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
