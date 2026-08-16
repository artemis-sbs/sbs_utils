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
def _button_promise ():
    """Lazy import: procedural.gui imports back into this module."""
def _cosmos_event_handler (sim, event):
    ...
def _dead_handler_sites ():
    ...
def _drops_size ():
    ...
def _log_size ():
    """Lazy import: procedural.log_panel is not needed until a reset audit runs."""
def _mast_expr_source_count ():
    ...
def _particle_count ():
    """How many attached emitters are live. Ledger probe."""
def _phase (store, name, fn, *args):
    """Time one phase of the event handler into `store` (name -> seconds).
    
    Used only to enrich the existing >33ms "Elapsed time" spike print with a
    per-phase breakdown (dispatch_tick / spawn / Gui.present / gc / dirty /
    delete), so a spike can be attributed to a subsystem live in the engine.
    Cost is one perf_counter pair per phase (~sub-microsecond); the breakdown is
    only printed on a frame that already exceeds the spike threshold."""
def _probe_agents () -> int:
    ...
def _probe_ship_data_extra ():
    """Reset-ledger probe: how many extra ship-data files this mission loaded.
    
    An unregistered per-mission container is invisible to the soak audit, and
    the whole point of the ledger is that nothing gets to be invisible."""
def _relic_contents_count ():
    """How many content records are armed. The reset-ledger probe - an armed record that
    survives a mission reset would place loot in the NEXT mission."""
def _relics_count ():
    """Number of registered relic records. The reset-ledger probe."""
def _report_reentry (event):
    ...
def _vocab_size ():
    ...
def _volume_anchor_count ():
    """Live tractor anchor objects. The reset-ledger probe."""
def _volume_count ():
    """Number of defined volumes. The reset-ledger probe."""
def _volume_watch_count ():
    """Number of live watchers. The reset-ledger probe."""
def amd_content_cache_size ():
    ...
def amd_cutscene_clear ():
    """Drop every loaded cutscene/rundown/cast - the per-mission reset."""
def amd_declared_addons_clear ():
    """Drop the cached addon list - the per-mission reset."""
def amd_doc_cache_clear ():
    """Per-mission: the next mission's files are different files."""
def amd_doc_cache_size ():
    ...
def amd_effects_count ():
    """Ledger probe."""
def amd_vocabulary_added ():
    """How many vocabulary entries exist beyond the library's own baseline.
    
    DELIBERATELY NOT on the reset ledger. The ledger means "this must be EMPTY after
    a reset", and vocabulary must survive one - so a probe here would report a leak
    on every run after the first and turn the restart soak into noise. This is a
    DIAGNOSTIC: when two missions declare one label differently, amd_register_fields
    raises at startup on a mission that was fine a moment ago, and this is the number
    that tells you the previous mission's words are still loaded."""
def clear_shared ():
    ...
def comms_history_clear ():
    """Per-mission state: last mission's conversations are not this one's."""
def comms_history_size ():
    """Probe for the reset ledger."""
def conformance_error_count ():
    """Runtime errors seen so far. Reset-ledger probe."""
def cosmos_event_handler (sim, event):
    """Engine entry point. Guards the non-reentrancy the rest of this file assumes."""
def dialogue_scenes_registry_clear ():
    """Drop the registry - the per-mission reset."""
def dialogue_slots_clear ():
    """Drop the registry - the per-mission reset."""
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
def gui_record_count ():
    """How many interactions have been recorded. Reset-ledger probe."""
def hail_reset ():
    """Drop module-level hail state for a mission reset.
    
    The per-ship records need nothing here: they live in ship inventory and go with
    `Agent.clear()`. Only the injected resolver outlives a mission, which is why it is
    a LATCH in the reset ledger rather than a container."""
def landmarks_registry_clear ():
    """Drop the declared-record registry - the per-mission reset."""
def lore_clear ():
    """Drop every registered source - the per-mission reset."""
def lore_sources ():
    """Registered sources, in registration order."""
def modifiers_count () -> int:
    """How many modifiers are live. Reset-ledger probe."""
def orbit_count ():
    """How many orbits are live. Cheap probe for tests, diagnostics and the reset ledger."""
def overlay_amd_clear ():
    """Drop the declared overlay records. CONTENT, not vocabulary: these come from a
    mission's .amd, so keeping them means run 2 can resolve a key only the PREVIOUS
    mission declared and fire the wrong card, silently. On the reset ledger, so a
    forgotten clear is reported by name instead of found three runs later."""
def overlay_amd_count ():
    ...
def overlay_live_clear ():
    """Drop every live-overlay record and the catch-up ticker (mission reset).
    
    Registered in handlerhooks' reset ledger. The ticker itself is already dropped
    by TickDispatcher.clear(), but the HANDLE has to go with it or _live_start()
    sees a task that no longer runs and never schedules a new one — the "already
    scheduled" latch that outlives the dispatcher."""
def particle_charge_count ():
    """Ledger probe: build-ups in flight."""
def particle_presets_mission_count ():
    """Ledger probe: how many mission-defined presets are live."""
def print_event (event):
    """Print the event data.
    Args:
        event (event): The event of interest."""
def quest_consoles_clear ():
    """Drop the quest-tab console names. CONTENT: a mission declares these from its
    own .mast at compile scope, so without a clear the set is add-only across an
    in-process reload and the next mission shows a Quests tab on consoles it never
    enabled."""
def quest_consoles_count ():
    ...
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
def timer_signals_count ():
    """How many timers/counters are armed to emit a signal (reset audit)."""
def viewscreen_helm_override (ship, view, facing, mode):
    """Helm touched the main-screen control: the viewer stands down.
    
    Called from the ``main_screen_change`` handler with the triple the engine just
    reported. No restore - helm's choice IS the new state, and putting the viewer's
    idea of "before" back over the top would undo the very change being handled.
    
    A triple identical to what the viewer asked for is NOT a takeover: a console
    reconnecting replays the state it is already in.
    
    The triple is written here as well as by the caller. ``handlerhooks`` already
    records it (issue #595) and writing it twice is harmless - but a function whose
    postcondition depends on the caller having gone first is a trap for the next
    caller, so this one leaves the ship in the state it was told about either way.
    
    Returns:
        bool: True if a viewer was stood down."""
def viewscreen_reset ():
    """Drop every running shot WITHOUT touching the engine - for mission reset.
    
    The tick tasks are already gone by then (``TickDispatcher.clear()``), and the
    clients these records name belong to a sim that is being torn down, so re-assigning
    their cameras is at best pointless. This just stops the records outliving the
    mission that made them."""
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
