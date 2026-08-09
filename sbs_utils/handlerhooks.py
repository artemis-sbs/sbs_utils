from .griddispatcher import GridDispatcher
from .damagedispatcher import DamageDispatcher, CollisionDispatcher
from .consoledispatcher import ConsoleDispatcher
from .tickdispatcher import TickDispatcher
from .lifetimedispatcher import LifetimeDispatcher
from .launchdispatcher import LaunchDispatcher
from .garbagecollector import GarbageCollector
from .delete_queue import DeleteQueue
from .extra_dispatcher import HotkeyDispatcher, ClientStringDispatcher
from .procedural.inventory import get_inventory_value, set_inventory_value


from .gui import Gui, Page
import traceback
from . import faces
from .fs import get_mission_name, get_startup_mission_name
from .vec import Vec3

from .agent import Agent, clear_shared
from .mast.mastscheduler import MastAsyncTask
from .helpers import FrameContext, Context, format_exception
import time
import gc


# --- GC policy (G2, see MAST_RUNTIME_IMPROVEMENTS.md) -------------------------
# The tick loop allocates many short-lived containers (symbol tables, eval
# namespaces, transient sets). CPython's default gen0 threshold (700 net
# container allocations) triggers a gen0 sweep several times PER TICK under
# load. Raising it trades a little peak memory for far fewer sweeps
# (bench: 77 -> a handful of collections over 300 ticks) with no behavior
# change: refcounting still frees non-cyclic garbage immediately, and cyclic
# garbage is still collected, just less often. sbs_utils owns the embedded
# runtime, so a one-time process-wide policy here is appropriate.
_GC_GEN0_THRESHOLD = 10000
_g0, _g1, _g2 = gc.get_threshold()
if _g0 < _GC_GEN0_THRESHOLD:
    gc.set_threshold(_GC_GEN0_THRESHOLD, _g1, _g2)


def _phase(store, name, fn, *args):
    """Time one phase of the event handler into `store` (name -> seconds).

    Used only to enrich the existing >33ms "Elapsed time" spike print with a
    per-phase breakdown (dispatch_tick / spawn / Gui.present / gc / dirty /
    delete), so a spike can be attributed to a subsystem live in the engine.
    Cost is one perf_counter pair per phase (~sub-microsecond); the breakdown is
    only printed on a frame that already exceeds the spike threshold.
    """
    _s = time.perf_counter()
    try:
        return fn(*args)
    finally:
        store[name] = store.get(name, 0.0) + (time.perf_counter() - _s)


# Every dispatcher/registry that accumulates per-mission state at COMPILE time and so
# must be wiped to (re)start a mission cleanly. The engine forks a fresh process per
# mission, so it never needs this; an in-process recompile (the dev runner's
# run_next_mission) does - otherwise the previous mission's routes/labels/globals/
# agents linger and the recompile fails or stale routes fire. Single source of truth so
# the reset can't drift across the runner, tests, and any future in-process reload.
#
# RESET LEDGER. The list below is hand-maintained, and every module-level container
# that is NOT on it becomes a "works on run 1, broken on run 2" bug - the engine's
# fresh process hides them, the dev runner's reused interpreter does not. Modules that
# own per-mission state register a size probe here; reset_mission_audit() then reports
# anything still holding data after a reset, so a forgotten clear FAILS A TEST instead
# of turning into a mystery three runs later. Probes must be cheap (a len()).
_RESET_PROBES: dict = {}


def register_reset_state(name: str, probe) -> None:
    """Declare a per-mission container that must be empty after reset_mission_state().

    `probe` returns its current size (an int). Registration is idempotent by name, so
    re-importing a module does not duplicate it.
    """
    _RESET_PROBES[name] = probe


def reset_mission_audit() -> dict:
    """Sizes of every registered container. Non-zero entries after a reset are leaks.

    Returns {name: size} for the NON-EMPTY ones only - an empty dict means clean.
    """
    out = {}
    for name, probe in _RESET_PROBES.items():
        try:
            n = int(probe())
        except Exception as e:            # a broken probe is itself worth reporting
            out[name] = f"probe error: {e}"
            continue
        if n:
            out[name] = n
    return out


def reset_mission_state():
    """Reset all per-mission runtime state for a fresh mission / in-process recompile."""
    for d in (GridDispatcher, DamageDispatcher, CollisionDispatcher, ConsoleDispatcher,
              TickDispatcher, LifetimeDispatcher, LaunchDispatcher, GarbageCollector,
              DeleteQueue, HotkeyDispatcher, ClientStringDispatcher):
        d.clear()
    # Decorator-label registries that accumulate at compile time (lazy import - these
    # live in mast_sbs.story_nodes, which imports back into the mast layer).
    from .mast_sbs.story_nodes.media import MediaLabel
    from .mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
    MediaLabel.clear()          # @media labels (folders APPENDS - reload would double)
    GuiTabDecoratorLabel.clear()  # //gui/tab labels
    # Navigation routes (//comms, //science, //gui/...) register their LABEL OBJECTS
    # here as they compile, and nothing emptied it - so a second compile in one
    # interpreter left the map holding two generations of the same routes. Navigating
    # then ran a label from the dead compile, and the first inline button inside it
    # re-entered by name against the live mast: `Jump to label "__route__science__360__"
    # command 4 not found`. build_navigation_buttons now also filters to the current
    # mast, so this is belt and braces - but an unbounded compile-time registry is
    # exactly what the ledger below exists to notice.
    from .procedural.gui.gui import ButtonPromise
    ButtonPromise.navigation_map.clear()
    # The ship's log (Log Panel). Per-mission by definition - last mission's traffic
    # in this one's log would be nonsense - and registered below so a forgotten clear
    # is reported by name rather than found three runs later.
    from .procedural.log_panel import log_clear
    log_clear()
    # A voice registered by the LAST mission names an agent that no longer exists.
    from .procedural.quest_driver import quest_dispatch_voice_clear
    quest_dispatch_voice_clear()
    from .procedural.amd_drops import drops_clear
    drops_clear()
    # Grav tethers. The engine holds the connections and _TETHERS holds the enforcement
    # state that drives them - neither was cleared, so a tether from the LAST mission
    # survived the reload and its per-tick enforcer kept capping a ship's throttle in
    # this one. Mounts (procedural.mount) need no entry here: they keep no module-level
    # registry, only Agent links that are purged with their objects.
    from .procedural.grav_tether import grav_tether_clear_all
    grav_tether_clear_all()
    # Mounts hold ENGINE tractor connections too. They need no ledger entry (their state
    # is Agent links and inventory, purged with the agents), but the welds themselves are
    # dropped here deliberately rather than left to the sim being recreated - and since
    # grav_tether_clear_all now deletes only ITS OWN connections, nothing else would.
    from .procedural.mount import mount_clear_all
    mount_clear_all()
    # Modifiers are a CLASS-level registry that nothing emptied, so a buff (or a tow drag)
    # applied in one mission was still live in the next one.
    from .procedural.modifiers import modifiers_reset
    modifiers_reset()
    # Camera + cutscene state. TickDispatcher.clear() above drops their DRIVER
    # tasks, but the dicts that say who owns which console outlive it - and a
    # stale owner makes the next mission's first move think it is being
    # superseded. Registered in the audit above, so a miss here is reported by
    # name rather than found later as "the camera does not move on run 2".
    _CAMERA_MOVES.clear()
    _CUTSCENES.clear()
    _PLAYING.clear()
    rundown_clear()     # shots AND both desks - a stale program audience would
                        # aim the next mission's punches at dead client ids
    viewscreen_reset()  # "on screen" shots. Records only - the consoles they name
                        # belong to the sim being torn down, so nothing is re-aimed
    comms_history_clear()   # who said what to whom. Per-mission by definition, and the
                            # keys are object ids that the next mission RECYCLES
    overlay_live_clear()  # live overlays awaiting late joiners; the catch-up ticker
                          # is dropped by TickDispatcher.clear() above, and a record
                          # left behind would re-deliver last mission's card
    amd_cutscene_clear()  # declared scenes/rundowns AND the cast bindings
    landmarks_registry_clear()  # declared landmark records an `Action:` line places by name
    lore_clear()                # Library sources registered by addons
    amd_declared_addons_clear()  # cached story.json addon list
    overlay_amd_clear()   # DECLARED overlay records read out of the mission's .amd.
                          # Distinct from `overlay_live_clear()` above, which drops the
                          # live cards: this is the catalogue they are looked up in, and
                          # keeping it let run 2 resolve a key only run 1 declared.
    quest_consoles_clear()  # which consoles show the Quests tab. A mission declares
                            # these at compile scope, so the set was add-only across a
                            # reload and the next mission inherited them.
    Agent.clear()       # all agents, roles, inventories, links
    clear_shared()      # rebuild the SHARED agent (drops label names / console types)
    from .procedural.signal import signal_waiters_clear
    signal_waiters_clear()  # drop pending signal_next() awaiters from the old mission
    from .procedural import brain as _brain
    _brain.brains_reset()   # release the brain re-entrancy guard + rolling slicer
    from .procedural.objective import objective_reset
    # MUST come after TickDispatcher.clear() above: it drops the tick tasks, and
    # this drops the "already scheduled" latches that would otherwise stop them
    # being re-registered - leaving the next mission with brains that never think.
    objective_reset()
    from .procedural.urge import urge_reset
    urge_reset()        # same latch as objective_reset: a stale "scheduled" global
                        # would leave every actor mute from run 2 onward, silently
    from .procedural.announce import announce_traffic_reset
    announce_traffic_reset()    # the "when did anything last speak" clock the urge
                                # budget's global floor reads
    from .procedural.terrain import terrain_sow_reset
    terrain_sow_reset() # queued terrain for a mission that is over, plus the "we
                        # are sowing" flag - left on, the next mission's terrain
                        # would queue against a dead tick task and never appear
    from .procedural.ship_data import ship_data_reset_for_mission
    ship_data_reset_for_mission()   # the loaded #ship-list, INCLUDING entries merged from
                                    # the old mission's extraShipData and its mods. The
                                    # next mission has its own mission dir and its own
                                    # mods; inheriting these spawns ships it never asked
                                    # for and hides ones it did.
    from .procedural.gui_record import gui_record_reset
    gui_record_reset()      # the transcript belongs to the mission that was recording
    from .procedural.conformance import conformance_reset
    conformance_reset()     # ...and so does the verdict
    from .procedural.ship_data_mod import ship_data_mod_reset
    ship_data_mod_reset()   # add-on ship entries belong to the mission that declared them;
                            # inheriting them would write ships the next mission never
                            # asked for into its folder.
    from .procedural.fleet_tables import fleet_tables_reset
    fleet_tables_reset()    # a race's fleet ladder belongs to the mission that enabled
                            # the race; inheriting it would let the next mission spawn
                            # fleets for a race it never turned on.
    from .procedural.grid import grid_reset_caches
    grid_reset_caches() # ship interiors + grid themes, same reason: _grid_data is the
                        # base table MERGED with the mission's own, and the theme index
                        # is a per-mission selection.
    Gui.web_client_ids.clear()  # drop web-page sessions from the old mission
    from .procedural.web import web_living_clear
    web_living_clear()  # drop living/persistent web-page registrations
    # Per-client pages LAST. A page holds a live gui_task whose label_stack and
    # active_label point at Label OBJECTS from the OLD compile. Agent.clear()
    # above drops the agents but not Gui.clients, so without this a surviving
    # page keeps ticking into a stale label after the recompile and dies with
    # `Jump to label "__route__gui/normal_sci__86__" command 23 not found` - the
    # command index is valid for the label it was compiled against, not the one
    # still being ticked. The caller re-fires client_connect, which rebuilds each
    # page against the fresh story.
    #
    # NOTE deliberately NOT resetting DecoratorLabel's id counter: distinct ids
    # across compiles are what make a stale reference fail LOUDLY. Reuse the ids
    # and a stale reference silently resolves to a DIFFERENT label of the same
    # name, which is far worse to debug than this error.
    Gui.clients.clear()
    # The engine's widget list belongs to the old mission's pages. Forget what
    # was sent so each rebuilt page establishes its own.
    Gui.widget_list_sent.clear()


def _log_size():
    """Lazy import: procedural.log_panel is not needed until a reset audit runs."""
    from .procedural.log_panel import log_size
    return log_size()


def _button_promise():
    """Lazy import: procedural.gui imports back into this module."""
    from .procedural.gui.gui import ButtonPromise
    return ButtonPromise


# Library-side probes. Each returns the count that MUST be zero once a reset has run.
# Agent.all keeps exactly one entry - the rebuilt SHARED agent - so it reports the
# excess over that rather than its raw size.
def _probe_agents() -> int:
    return max(0, len(Agent.all) - 1)


register_reset_state("Agent.all", _probe_agents)
register_reset_state("Gui.clients",       lambda: len(Gui.clients))
register_reset_state("Gui.web_client_ids", lambda: len(Gui.web_client_ids))
register_reset_state("Gui.widget_list_sent", lambda: len(Gui.widget_list_sent))
# Route labels registered per compile. Unregistered until 2026-08-06, which is why it
# grew silently across compiles instead of being reported by name.
register_reset_state("log_panel", lambda: _log_size())
from .procedural.quest_driver import _QUEST_DISPATCH_VOICE
register_reset_state("quest dispatch voice",
                     lambda: 1 if _QUEST_DISPATCH_VOICE[0] is not None else 0)
from .procedural.amd_drops import drops_size as _drops_size
register_reset_state("drop tables", _drops_size)
from .procedural.grav_tether import _TETHERS as _GRAV_TETHERS
register_reset_state("grav tethers",       lambda: len(_GRAV_TETHERS))
from .procedural.modifiers import modifiers_count
register_reset_state("modifiers",          modifiers_count)
register_reset_state("ButtonPromise.navigation_map",
                     lambda: sum(len(v) for v in _button_promise().navigation_map.values()))
register_reset_state("TickDispatcher",    lambda: len(TickDispatcher._dispatch_tick))
# Registered HERE rather than from camera.py, whose own import of this module is
# circular - and a swallowed ImportError would have left the container invisible to
# the audit, which is exactly the leak the ledger exists to catch.
from .procedural.gui.camera import _MOVES as _CAMERA_MOVES
register_reset_state("camera moves",      lambda: len(_CAMERA_MOVES))
from .procedural.gui.cutscene import _CUTSCENES, _PLAYING
register_reset_state("cutscenes",         lambda: len(_CUTSCENES))
register_reset_state("cutscenes playing", lambda: len(_PLAYING))
from .procedural.gui.rundown import _SHOTS as _RUNDOWN_SHOTS, rundown_clear
register_reset_state("rundown shots",     lambda: len(_RUNDOWN_SHOTS))
from .procedural.gui.viewscreen import (_VIEWERS as _VIEWSCREEN_SHOTS, viewscreen_reset,
                                        viewscreen_helm_override)
register_reset_state("viewscreen shots",  lambda: len(_VIEWSCREEN_SHOTS))
from .procedural.comms import comms_history_clear, comms_history_size
register_reset_state("comms history",     comms_history_size)
from .procedural.gui.overlay import _LIVE as _OVERLAY_LIVE, overlay_live_clear
register_reset_state("overlays live",     lambda: len(_OVERLAY_LIVE))
from .procedural.amd_cutscene import (CUTSCENE_AMD, RUNDOWN_AMD, CUTSCENE_CAST,
                                      amd_cutscene_clear)
register_reset_state("amd cutscenes",     lambda: len(CUTSCENE_AMD))
register_reset_state("amd rundowns",      lambda: len(RUNDOWN_AMD))
register_reset_state("cutscene cast",     lambda: len(CUTSCENE_CAST))
from .procedural.amd_landmarks import _RECORDS as _AMD_LANDMARKS, landmarks_registry_clear
register_reset_state("amd landmarks",     lambda: len(_AMD_LANDMARKS))
from .procedural.amd_doc import (lore_clear, lore_sources,
                                 amd_declared_addons_clear, _DECLARED_ADDONS)
register_reset_state("lore sources",      lambda: len(lore_sources()))
from .procedural.terrain import terrain_sow_pending
register_reset_state("terrain sow",       terrain_sow_pending)
# Ship + interior data. These look like read-only caches of engine files and are not:
# each is the base table MERGED with what the mission (and, later, its mods) added, so
# they are per-mission state. A mod system makes an unreset one a correctness bug -
# mission B silently inheriting mission A's ships and interiors.
from .procedural.ship_data import ship_data_is_loaded
register_reset_state("ship_data_cache",   ship_data_is_loaded)
from .procedural.grid import (grid_data_is_loaded, grid_theme_is_loaded,
                              grid_theme_current_index)
register_reset_state("grid_data",         grid_data_is_loaded)
register_reset_state("grid_theme",        grid_theme_is_loaded)
register_reset_state("grid_theme_current", grid_theme_current_index)
from .procedural.fleet_tables import fleet_tables_count
register_reset_state("fleet_tables",      fleet_tables_count)
from .procedural.ship_data_mod import ship_data_pending_count
register_reset_state("ship_data_mod",     ship_data_pending_count)
from .procedural.gui_record import gui_record_count
register_reset_state("gui_record",        gui_record_count)
from .procedural.conformance import conformance_error_count
register_reset_state("conformance",       conformance_error_count)
register_reset_state("amd declared addons", lambda: len(_DECLARED_ADDONS))
from .procedural.amd_overlay import overlay_amd_clear, overlay_amd_count
register_reset_state("amd overlays",      overlay_amd_count)
from .procedural.quest import quest_consoles_clear, quest_consoles_count
register_reset_state("quest consoles",    quest_consoles_count)

# --- VOCABULARY, and why it is NOT on the list above ------------------------
# The registries below (AMD field tables, stage-direction verbs, dialogue surfaces,
# urge conditions, the landmark placer) look like the same kind of module-level
# per-mission state, and clearing them would be a run-2 bug in the OTHER direction.
# They are populated at module IMPORT time, and `MastGlobals.mission_py_modules` is
# not reset while `Mast.import_python_module_for_source` dedupes by file - so on an
# in-process recompile a mission's `*_amd.py` is NOT re-executed and nothing would
# re-register what a clear had just deleted. The mission would lose its own words.
#
# What IS worth watching is the DELTA: the library's own baseline is fine, a
# MISSION's additions surviving into the next mission are not - two missions that
# declare the same label differently make amd_register_fields raise at startup, on
# a mission that was fine a moment ago. So these probes report growth, not size.
from .procedural import amd_schema as _amd_schema
from .procedural import amd_action as _amd_action
from .procedural import amd_dialogue as _amd_dialogue
from .procedural import urge as _urge


def _vocab_size():
    return (sum(len(t) for t in _amd_schema.ARCHETYPES.values())
            + sum(len(t) for t in _amd_schema.TRAITS.values())
            + len(_amd_schema._SECTION_ALIASES) + len(_amd_schema._PARSERS)
            + len(_amd_action._VERBS) + len(_amd_dialogue._DIRECTIONS)
            + len(_urge._CONDITIONS))


_VOCAB_BASELINE = _vocab_size()   # the LIBRARY's own vocabulary, at import


def amd_vocabulary_added():
    """How many vocabulary entries exist beyond the library's own baseline.

    DELIBERATELY NOT on the reset ledger. The ledger means "this must be EMPTY after
    a reset", and vocabulary must survive one - so a probe here would report a leak
    on every run after the first and turn the restart soak into noise. This is a
    DIAGNOSTIC: when two missions declare one label differently, amd_register_fields
    raises at startup on a mission that was fine a moment ago, and this is the number
    that tells you the previous mission's words are still loaded.
    """
    return max(0, _vocab_size() - _VOCAB_BASELINE)
register_reset_state("DeleteQueue",       lambda: len(DeleteQueue._pending) + len(DeleteQueue._pending_grid))
register_reset_state("Agent.roles",       lambda: len(Agent.roles.collections))
register_reset_state("Agent.has_links",   lambda: len(Agent.has_links.collections))
register_reset_state("Agent._has_inventory", lambda: len(Agent._has_inventory.collections))
# Not a container - a latch. Stuck on means NO brain will ever run again, so every
# NPC stops thinking with no error. Worth a ledger entry precisely because it is
# silent.
register_reset_state("brain.stalled",
                     lambda: 1 if __import__("sbs_utils.procedural.brain", fromlist=["x"]).brains_is_stalled() else 0)
# Also a latch, not a container: "scheduled" but the dispatcher no longer holds the
# task means brains and objectives are dead for the rest of the process.
register_reset_state("objective.ticks_stale",
                     lambda: 1 if __import__("sbs_utils.procedural.objective", fromlist=["x"]).objective_ticks_stale() else 0)
# The urge ticker's latch, for the same reason: set-but-unscheduled means no actor ever
# speaks again, with no error to show for it.
register_reset_state("urge.ticks_stale",
                     lambda: 1 if __import__("sbs_utils.procedural.urge", fromlist=["x"]).urge_ticks_stale() else 0)
# The speech budget's per-actor clocks. Carried into the next mission they would mute
# actors for the first 45 seconds of it, for no reason anyone could see.
register_reset_state("urge.speech clocks",
                     lambda: len(__import__("sbs_utils.procedural.urge", fromlist=["x"])._last_actor_spoke))


#	client_id"
#	parent_id"
#	origin_id"
#	selected_id"
#	tag"
#	sub_tag"
#	value_tag"
#	source_point"
#	event_time"
#	sub_float"
def print_event(event):
    """
    Print the event data.
    Args:
        event (event): The event of interest.
    """
    print(f"client ID {event.client_id}")
    print(f"Parent ID {event.parent_id}")
    print(f"Origin ID {event.origin_id}")
    print(f"Selected ID {event.selected_id}")
    print(f"Tag {event.tag}")
    print(f"Sub Tag {event.sub_tag}")
    print(f"Sub Float {event.sub_float}")
    print(f"Value Tag {event.value_tag}")
    print(f"Extra Tag {event.extra_tag}")
    print(f"Extra Extra Tag {event.extra_extra_tag}")
    print(f"Point {event.source_point.x}  {event.source_point.y} {event.source_point.z}")


class ErrorPage(Page):
    def __init__(self, msg) -> None:
        self.gui_state = 'show'
        self.message = msg
        self.gui_task = None
        

    def present(self, event):
        SBS = FrameContext.context.sbs
        match self.gui_state:
            case  "sim_on":
                self.gui_state = "blank"
                Gui.root_clear(SBS, event.client_id)
                SBS.send_gui_complete(event.client_id, "")

            case  "show":
                Gui.root_clear(SBS, event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                print(self.message)
                self.message = self.message.replace(",", ".")
                self.message = self.message.replace(";", ".")
                self.message = self.message.replace(":", ".")
                SBS.send_gui_text(
                    event.client_id,"", "text", f"$text:sbs_utils runtime error^{self.message};", 0, 0, 80, 95)
                
                # SBS.send_gui_button(event.client_id, "back", "$text:pause mission;", 0, 80, 20, 94)
                SBS.send_gui_button(event.client_id,"", "resume", "$text:Resume Mission;", 25, 80, 45, 99)
                SBS.send_gui_button(event.client_id,"", "rerun", "$text:Rerun Mission;", 50, 80, 70, 99)
                SBS.send_gui_button(event.client_id,"", "startup", "$text:run startup Mission;", 75, 80, 99, 99)
                SBS.send_gui_complete(event.client_id, "")

    def on_message(self, event):
        SBS = FrameContext.context.sbs
        match event.sub_tag:
            # case "back":
            #     self.gui_state = "sim_on"
            #     self.present(event)

            #     Gui.pop(event.client_id)
            #     FrameContext.context.sbs.pause_sim()

            case "resume":
                self.gui_state = "sim_on"
                self.present(event)

                Gui.pop(event.client_id)
                SBS.resume_sim()

            case "rerun":
                self.gui_state = "sim_on"
                self.present(event)

                Gui.pop(event.client_id)
                start_mission = get_mission_name()
                SBS.run_next_mission(start_mission)

            case "startup":
                self.gui_state = "sim_on"
                self.present(event)

                Gui.pop(event.client_id)
                start_mission = get_startup_mission_name()
                if start_mission is not None:
                    SBS.run_next_mission(start_mission)

def tick_the_rest(event):
    TickDispatcher.dispatch_tick()
    Gui.present(event)
    # `test=<seconds>` writes a conformance verdict once the mission has run that long.
    # Costs one resolved integer when not requested. Here because it is the one place
    # reached every tick regardless of which event arrived.
    from .procedural.conformance import conformance_tick
    conformance_tick()


def _cosmos_event_handler(sim, event):
    try:
        #t = time.process_time()
        t = time.perf_counter()
        phase_ms = {}   # per-phase timing; printed only on a >33ms spike
        import sbs
        from .procedural.signal import signal_emit
        # Allow guis more direct access to events
        # e.g. Mast Story Page, Clients change
        ctx = Context(sim, sbs, event)
        FrameContext.context = ctx
        SBS = FrameContext.context.sbs
        # gui = Gui.clients.get(event.client_id):
        # if gui is not None:
        #     FrameContext.page = gui.page

        ### If there is a top level exception
        ### Only run the error page
        ### Any other event will likely cause an error
        ### and clear this error, 
        ### and could queue up a bunch of error pages
        server = FrameContext.server_page
        if isinstance(server, ErrorPage):
            if event.tag == "gui_message":
                server.on_message(event)
            return


        Agent.SHARED.set_inventory_value("sim", sim)
        # if event.tag != "mission_tick":
        #print_event(event)
        # if event.tag != "mission_tick":
        #     print(f"{event.tag}")
        match(event.tag):
            #	value_tag"
            #	source_point"
            #	event_time"
            #    print(f"{event.parent_id}")
            #     print(f"{event.origin_id}")
            #     print(f"{event.selected_id}")
            #     print(f"{event.sub_tag}")
            #     print(f"{event.sub_float}")
            # case "present_gui":
            #     Agent.SHARED.set_inventory_value("SIM_STATE", "sim_paused")
            #     Gui.present(event)

            case "screen_size":
                # gui = Gui.clients.get(event.client_id)
                # if gui is not None:
                #     gui.present(Context(sim, sbs, None), event)
                ar = Vec3(event.source_point.x, event.source_point.y,event.source_point.z)

                #
                # Only refresh when the size actually changed. The engine can
                # re-report the viewport several times for a single resolution
                # change (the new layout alters the usable area, which is
                # reported again). Without this guard every duplicate forces a
                # full gui refresh, which can look like the console "running
                # multiple times" and can feed a resize->refresh->resize loop.
                #
                prev = FrameContext.aspect_ratios.get(event.client_id)
                if prev is not None and prev.x == ar.x and prev.y == ar.y:
                    tick_the_rest(event)
                else:
                    FrameContext.aspect_ratios[event.client_id] = ar
                    Gui.on_event(event)
                    tick_the_rest(event)
            case "client_change":
                if event.sub_tag == "change_console":
                    Gui.on_event(event)
                tick_the_rest(event)

            case "main_screen_change":
                origin = event.origin_id
                # Setting the inventory fixes issue #595 where a new mainscreen view always starts in forward 3d view.
                set_inventory_value(origin, "MAIN_SCREEN_VIEW", event.sub_tag)
                set_inventory_value(origin, "MAIN_SCREEN_FACING", event.value_tag)
                set_inventory_value(origin, "MAIN_SCREEN_MODE", event.extra_tag)
                # Helm reaching for the main-screen control takes the screen back from
                # whoever was driving it - science's "on screen" (VIEWSCREEN_PLAN.md).
                # Compared against what the viewer asked for, so a console replaying
                # the state it is already in is not a takeover.
                viewscreen_helm_override(origin, event.sub_tag, event.value_tag,
                                         event.extra_tag)
                Gui.on_event(event)
                tick_the_rest(event)
            
            case "mission_tick":
                
                #
                # set the simulation state variable
                #
                # either sim_paused, or sim_running
                #
                Agent.SHARED.set_inventory_value("SIM_STATE", event.sub_tag)
                #Agent.SHARED.set_inventory_value("SIM_STATE", "sim_running")
                # Give a few ticks (NOT NEEDED This would not tick Gui)
                #for x in range(5):
                # dispatch_tick runs the shared per-second driver
                # (objectives/brains/scan/game-end); brains_run_all is the usual
                # periodic-spike culprit here. Gui.present ticks all MAST story
                # tasks (per client) then renders.
                _phase(phase_ms, "dispatch_tick(brains/timers)", TickDispatcher.dispatch_tick)
                # after tick task handle any lifetime events
                _phase(phase_ms, "spawn", LifetimeDispatcher.dispatch_spawn)
                # Run Guis, tick task
                _phase(phase_ms, "gui_present(MAST+render)", Gui.present, event)
 
            case "damage":
                #print_event(event)
                DamageDispatcher.dispatch_damage(event)
                LifetimeDispatcher.dispatch_damage(event)
                tick_the_rest(event)

            case "npc_killed":
                #print_event(event)
                DamageDispatcher.dispatch_killed(event)
                tick_the_rest(event)
                #LifetimeDispatcher.dispatch_damage(event)

            case "station_killed":
                #print_event(event)
                DamageDispatcher.dispatch_killed(event)
                tick_the_rest(event)
                #LifetimeDispatcher.dispatch_damage(event)
                


            case "red_alert":
                # get_inventory_value(event.client_id, "assigned_ship", None)
                ship_id = SBS.get_ship_of_client(event.client_id) 
                if ship_id is not None:
                    set_inventory_value(ship_id, "red_alert", event.value_tag == "on")
                    signal_emit("red_alert_change", {"SHIP_ID": ship_id, "RED_ALERT_STATUS": event.value_tag == "on"})
                tick_the_rest(event)


            case "player_internal_damage":
                DamageDispatcher.dispatch_internal(event)
                tick_the_rest(event)

            case "heat_critical_damage":
                #print_event(event)
                DamageDispatcher.dispatch_heat(event)
                tick_the_rest(event)

            case "passive_collision_start":
                #print_event(event)
                CollisionDispatcher.dispatch_passive(event)
                tick_the_rest(event)

            case "passive_collision_end":
                #print_event(event)
                CollisionDispatcher.dispatch_passive(event)
                tick_the_rest(event)

            case "player_launches_missile":
                # print_event(event)
                LaunchDispatcher.dispatch_missile(event)
                tick_the_rest(event)

            case "ship_launches_drone":
                # print_event(event)
                LaunchDispatcher.dispatch_drone(event)
                tick_the_rest(event)
            #TODO: Obsolete?
            case "passive_collision":
                #print_event(event)
                CollisionDispatcher.dispatch_passive(event)
                tick_the_rest(event)
                
            #TODO: Obsolete?
            case "interactive_collision":
                #print_event(event)
                CollisionDispatcher.dispatch_interactive(event)
                tick_the_rest(event)

            case "interactive_collision_start":
                #print_event(event)
                CollisionDispatcher.dispatch_interactive(event)
                tick_the_rest(event)

            case "interactive_collision_end":
                #print_event(event)
                CollisionDispatcher.dispatch_interactive(event)
                tick_the_rest(event)

            ## TODO: Add routes and leverage in docking, and pickups
            case "within_range":
                #print_event(event)
                CollisionDispatcher.dispatch_interactive(event)
                tick_the_rest(event)

            case "client_connect":
                Gui.add_client(event)
                tick_the_rest(event)

            case "select_space_object":
                # print_event(event)
                if "comms_sorted_list" == event.value_tag or "comms_2d_view" == event.value_tag:
                    SBS.send_comms_selection_info(event.origin_id, "", "white", "static")
                #
                # Avoid obscure bug, waterfall send selected_id == 0
                #
                if event.selected_id==0 and "comms_waterfall" == event.value_tag:
                    SBS.send_comms_selection_info(event.origin_id, "", "white", "static")
                    return
                    

                ConsoleDispatcher.dispatch_select(event)

            case "hold_button_pressed":
                #print_event(event)
                ConsoleDispatcher.dispatch_message(event, f"{event.sub_tag}_popup")
                tick_the_rest(event)

            case "hold_click":
                #print_event(event)
                ConsoleDispatcher.dispatch_select(event)
                tick_the_rest(event)

            case "press_comms_button":
                # print_event(event)
                ConsoleDispatcher.dispatch_message(event, "comms_target_UID")
                tick_the_rest(event)

            case "client_string":
                # print_event(event)
                ClientStringDispatcher.dispatch(event)
                tick_the_rest(event)

            case "science_scan_complete":
                #print_event(event)
                ConsoleDispatcher.dispatch_message(event, "science_target_UID")
                tick_the_rest(event)

            case "gui_message":
                #print_event(event)
                Gui.on_message(event)
                tick_the_rest(event)                
            case "grid_object":
                #print_event(event)
                GridDispatcher.dispatch_grid_event(event)
                tick_the_rest(event)

            case "grid_object_selection":
                # Set Comms info to empty
                SBS.send_grid_selection_info(event.parent_id, "", "white", "")
                ConsoleDispatcher.dispatch_select(event)
                tick_the_rest(event)
                
            case "press_grid_button":
                ConsoleDispatcher.dispatch_message(event, "grid_selected_UID")
                tick_the_rest(event)
                
            case "grid_point_selection":
                SBS.send_grid_selection_info(event.parent_id, "", "white", "")
                GridDispatcher.dispatch_grid_event(event)
                tick_the_rest(event)

            case "fighter_requests_dock":
                LifetimeDispatcher.dispatch_dock(event)
                tick_the_rest(event)

            case "press_fighter_button":
                # print_event(event)
                from .procedural.signal import signal_emit
                fighter = Agent.get(event.origin_id)
                if fighter is not None:
                    signal_emit("press_fighter_button", {"EVENT": event, "client_id": event.client_id, "FIGHTER": fighter, "FIGHTER_ID": event.origin_id, "button": event.sub_tag})
                tick_the_rest(event)
                

            case "docking_change":
                # print_event(event)
                from .procedural.docking import docking_run_all
                docking_run_all(event)
                tick_the_rest(event)
        
            case _:
                print (f"Unhandled event {event.client_id} {event.tag} {event.sub_tag}")
                tick_the_rest(event)
        #
        # Call the garbage collector
        # Well behaved things will register 
        # with the garbage collector
        # with IDs and a callback
        # When the ID is no longer valid the callback is called
        _phase(phase_ms, "gc", GarbageCollector.collect)
        # Backstop for finished MAST tasks that never passed through the
        # scheduler's done-list (sub-tasks of a parent that stopped ticking,
        # route/comms tasks run to completion in place). Without this they stay
        # in Agent.all + the role/inventory registries for the whole mission.
        _phase(phase_ms, "task_sweep", MastAsyncTask.sweep_finished)
        from .pages.layout.dirty import Dirty
        _phase(phase_ms, "dirty", Dirty.represent_dirty)

        # Deferred native frees: every task this tick has yielded, so it is now
        # safe to actually free objects that were tombstoned by delete_object().
        # Guard the (common) empty case at the call site to skip the method call.
        if DeleteQueue.has_pending():
            _phase(phase_ms, "delete", DeleteQueue.drain)

        Agent.SHARED.set_inventory_value("sim", None)
        Agent.context = None

        #et = time.process_time() - t
        et = time.perf_counter() - t
        if et > 0.033:
            # Attribute the spike: which phase(s) dominated this frame.
            brk = "  ".join(f"{k}={v*1000:.0f}ms"
                            for k, v in sorted(phase_ms.items(), key=lambda kv: -kv[1])
                            if v > 0.001)
            print(f"Elapsed time: {et:.4f} {event.tag}-{event.sub_tag} | {brk}")

    except BaseException as err:
        SBS.pause_sim()
        text_err = format_exception("", "SBS Utils Hook level Runtime Error:")
        text_err += traceback.format_exc()
        text_err = text_err.replace(chr(94), "")
        print(text_err)
        #
        # Make sure we don't show more that one error
        #
        FrameContext.error_message = text_err
        #Gui.push(0, ErrorPage(text_err))
    # 
    # This is useful for client errors get shown on server
    #
    if len(FrameContext.error_message) > 0:
        text_err = FrameContext.error_message
        FrameContext.error_message = ""
        Gui.push(0, ErrorPage(text_err))



#
# Nothing in this file is safe to re-enter. The handler installs ONE global
# context (`FrameContext.context = ctx`) and nulls the sim on the way out, so a
# nested call would hand the outer frame the inner event's client and a dead
# sim - and the damage would surface far from here, as a NoneType on something
# that was live a moment earlier, or work done against the wrong console.
#
# We have never verified that the engine cannot do this. It is only known that
# the MOCK does not, which is no evidence at all: `sbs` calls run engine C++
# synchronously inside our frame (that is what the delete_object use-after-free
# was), so a call that builds native widgets could pump the engine's event queue
# and land us right back here.
#
# So state the assumption instead of trusting it. One list append per event, and
# it says something exactly once, the first time it is ever wrong.
#
_EVENT_STACK = []
_REENTRY_REPORTED = False


def _report_reentry(event):
    global _REENTRY_REPORTED
    if _REENTRY_REPORTED:
        return
    _REENTRY_REPORTED = True
    inner = f"{getattr(event, 'tag', '?')}/{getattr(event, 'sub_tag', '')}"
    import logging
    msg = ("REENTRANT cosmos_event_handler: "
           f"{' -> '.join(_EVENT_STACK)} -> {inner}. The engine called back into "
           "the handler before the outer event finished. FrameContext.context is "
           "a single global and the sim is nulled on exit, so the outer frame is "
           "now running against the wrong event. Reported once per session.")
    # Logged, not printed: engine print output reaches no file, so a print here
    # would be invisible in the one place this can actually happen.
    logging.getLogger("mast.runtime").error(msg)


def cosmos_event_handler(sim, event):
    """Engine entry point. Guards the non-reentrancy the rest of this file assumes."""
    if _EVENT_STACK:
        _report_reentry(event)
    _EVENT_STACK.append(f"{getattr(event, 'tag', '?')}/{getattr(event, 'sub_tag', '')}")
    try:
        return _cosmos_event_handler(sim, event)
    finally:
        _EVENT_STACK.pop()


GridDispatcher, DamageDispatcher, CollisionDispatcher,ConsoleDispatcher, TickDispatcher, LifetimeDispatcher, LaunchDispatcher
