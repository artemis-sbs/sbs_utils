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
from sbs_utils.dragdispatcher import DragDispatcher
from sbs_utils.launchdispatcher import LaunchDispatcher
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def _await_gui_sites ():
    ...
def _boarding_figure_count ():
    """Reset-ledger probe: bodies still standing on one."""
def _boarding_fire_count ():
    """Reset-ledger probe: consoles left holding a live weapon."""
def _boarding_invite_count ():
    """Reset-ledger probe."""
def _boarding_room_count ():
    """Reset-ledger probe: rooms the party is believed to be standing in."""
def _boarding_scene_count ():
    """Reset-ledger probe: whether a beat is being held."""
def _boarding_site_count ():
    """Reset-ledger probe: interiors still marked as being boarded."""
def _boarding_team_count ():
    """Reset-ledger probe: how many clients are bound to a character."""
def _button_promise ():
    """Lazy import: procedural.gui imports back into this module."""
def _cosmos_event_handler (sim, event):
    ...
def _crew_complement_count ():
    """Reset-ledger probe: how many automatic names are allocated to seats.
    
    A third probe rather than a bigger one, for the same reason `crew_seat_count` is separate:
    a complement that survives into the next mission is a DIFFERENT bug from a leaked seat -
    it shows up as run 2 naming its bridge after run 1's, or eventually as a pool with no free
    names left."""
def _crew_count ():
    """Reset-ledger probe: how much DECLARED roster data is held."""
def _crew_seat_count ():
    """Reset-ledger probe: how many LIVE seats are held.
    
    Separate from :func:`crew_count` on purpose - declared rosters and occupied seats leak
    for different reasons, and one probe covering both cannot say which of them happened."""
def _dead_handler_sites ():
    ...
def _drops_size ():
    ...
def _epadd_apps_count ():
    """Reset-ledger probe. `Agent.SHARED` is rebuilt by `clear_shared()` on every
    mission reset, so this should always report 0 after one - it is registered so that
    a future move off SHARED cannot go unnoticed."""
def _eva_route_count ():
    """Reset-ledger probe: consoles still flying a route."""
def _eva_suit_count ():
    """Reset-ledger probe: suits still in the world."""
def _face_mod_size ():
    """Reset-ledger probe: how much mod registration is currently held."""
def _log_size ():
    """Lazy import: procedural.log_panel is not needed until a reset audit runs."""
def _mast_expr_source_count ():
    ...
def _messages_count ():
    """Reset-ledger probe."""
def _messages_pending ():
    """Reset-ledger probe for the undelivered pile."""
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
def _standby_parked_count ():
    """Reset-ledger probe: parked loose objects + parked fleets."""
def _vocab_size ():
    ...
def _volume_anchor_count ():
    """Live tractor anchor objects. The reset-ledger probe."""
def _volume_count ():
    """Number of defined volumes. The reset-ledger probe."""
def _volume_watch_count ():
    """Number of live watchers. The reset-ledger probe."""
def _xess_log_count (kind=None):
    """How many readings there are. What the tile's badge says."""
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
def amd_sides_audience_count ():
    """Reset-ledger probe: how many token rules are held."""
def amd_sides_clear ():
    """Drop the cross-document side registries - the per-mission reset."""
def amd_theater_clear ():
    """Drop every declared theater. Called from reset_mission_state()."""
def amd_theater_count ():
    """How many theaters are declared - the reset-ledger probe."""
def amd_vocabulary_added ():
    """How many vocabulary entries exist beyond the library's own baseline.
    
    DELIBERATELY NOT on the reset ledger. The ledger means "this must be EMPTY after
    a reset", and vocabulary must survive one - so a probe here would report a leak
    on every run after the first and turn the restart soak into noise. This is a
    DIAGNOSTIC: when two missions declare one label differently, amd_register_fields
    raises at startup on a mission that was fine a moment ago, and this is the number
    that tells you the previous mission's words are still loaded."""
def art_keys_cache_clear ():
    """Drop the generated ART_KEYS pairing. On the reset ledger with the theaters."""
def clear_shared ():
    ...
def comms_history_clear ():
    """Per-mission state: last mission's conversations are not this one's."""
def comms_history_size ():
    """Probe for the reset ledger."""
def conformance_error_count ():
    """Runtime errors seen so far. Reset-ledger probe."""
def cosmos_event_handler (sim, event):
    """Engine entry point. Guards the non-reentrancy the rest of this file assumes.
    
    It also FREEZES the event on the way in, when the event knows how. The engine's
    own event is a Pybind11 object with read-only attributes; the mock's FakeEvent
    is a plain Python object that takes an assignment happily. That difference hid a
    real defect - code that re-stamped `event.sub_tag` to carry an arbitrated value
    onward passed the whole suite and raised on a live bridge. Freezing here makes
    the mock refuse it too, at the one place every event goes through.
    
    Nothing in the library writes to an event, so this asserts an invariant rather
    than changing behavior. A real engine event has no `freeze`, and is skipped."""
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
def grid_interior_pending ():
    """Ships recorded but not yet built, plus queued work still to run."""
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
def player_roster_clear ():
    """Drop every record and binding. On the reset ledger."""
def player_roster_count_records ():
    """How much state is held. The reset-ledger probe."""
def player_roster_crew_warn_count ():
    """How many unloaded CREW_HULL keys have been reported. On the reset ledger."""
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
def races_clear ():
    """Drop every declared race override. Called from reset_mission_state()."""
def races_count ():
    """How many race overrides are declared - the reset-ledger probe."""
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
def viewscreen_helm_override (ship, view, facing, mode, client_id=None):
    """Helm or weapons touched the engine's main-screen control.
    
    Called from the ``main_screen_change`` handler with the triple the engine just
    reported. What happens next depends on WHO holds the screen:
    
    * **A console claim** - science's "on screen", weapons', docking's - stands
      down, and nothing is restored: helm's choice IS the new state, and putting a
      recorded "before" back over the top would undo the very change being handled.
      Any request parked behind a story beat is thrown away too; helm just spoke,
      and a stale drop-down pick firing later would override the officer who
      overrode it.
    * **A story claim** - a cutscene, a hail, a mission beat - does NOT stand down.
      The crew's press is PARKED and applied when the story releases, so it is
      honored a few seconds late rather than lost, and the story's own triple is
      written back so the engine and the record agree again.
    
    **WHO pressed decides, not what the values are.** Only helm and weapons carry
    the ``main_screen_control`` widget; a main screen's widget list is
    ``3dview^ship_data`` / ``2dview^ship_data``, so a main screen cannot press one
    at all - every ``main_screen_change`` carrying a main screen's client id is
    that screen reporting back what we set it to. So an event from one of this
    ship's main screens is never a takeover, and an event from anywhere else
    always is.
    
    Comparing the reported triple against ``VIEWER_EXPECT`` instead was wrong in
    both directions, and each cost a real bug:
    
    * **The dial forces the view back to 3D.** Touching FRONT or CHASE means "show
      me that camera", so during a 3D shot it sends ``("3d_view", facing, mode)``
      - which is exactly what the shot recorded. Helm's press was read as a replay
      and swallowed; the engine moved the camera anyway (the flash), and the shot
      that was never stood down re-aimed it a moment later. Reported as science
      stealing the screen back.
    * **The shot cancelled itself.** Every shot goes through
      ``gui_cinematic_full_control``, which calls ``set_main_view_modes(cid,
      "3dview", "front", "cinematic")``. Coming back as an event that matches
      nothing, it read as a takeover - the viewer's own camera standing the viewer
      down.
    
    ``client_id=None`` keeps the old value comparison, for a caller that cannot say
    who pressed.
    
    The triple is written here as well as by the caller. ``handlerhooks`` already
    records it (issue #595) and writing it twice is harmless - but a function whose
    postcondition depends on the caller having gone first is a trap for the next
    caller, so this one leaves the ship in the state it was told about either way.
    On the story path that means writing the story's triple BACK over what the
    caller just recorded, which is the whole point.
    
    Returns:
        bool: True if a claim was stood down. False for a story claim that held -
        see ``viewscreen_effective_state`` for what the screen is actually showing
        afterwards, which is what the reroute has to carry."""
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
