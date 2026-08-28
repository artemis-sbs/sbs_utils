"""Viewscreen state + arbitration - "on screen" driven from another console.

Phase 1 of VIEWSCREEN_PLAN.md: no camera, no column. What is under test is who owns a
ship's main screen, what it is pointed at, and what happens when helm reaches for the
main-screen control while a viewer is running.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural.gui.camera import _MOVES
from sbs_utils.procedural.gui.viewscreen import (
    MODES, viewscreen_set, viewscreen_clear, viewscreen_mode, viewscreen_subject,
    viewscreen_is_live, viewscreen_consoles, viewscreen_helm_override,
    viewscreen_framing, viewscreen_home_ship, viewscreen_reset, _VIEWERS)


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


# Real-shaped console ids - the client bit is what makes consoles_of() treat them as
# consoles rather than as space objects.
C1 = 0x8000000000000001
C2 = 0x8000000000000002


def _console(cid, ship_id, *roles):
    """A console agent of the shape the audience resolver expects."""
    agent = Agent()
    agent.id = cid
    agent.add()
    for r in roles:
        add_role(cid, r)
    link(ship_id, "consoles", cid)
    return cid


class TestViewscreenState(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.target = to_id(player_spawn(1000, 0, 0, "Intrepid", "tsn", "battle"))

    def tearDown(self):
        FrameContext.context = None

    # --- the state itself -------------------------------------------------
    def test_starts_off(self):
        self.assertEqual(viewscreen_mode(self.ship), "off")
        self.assertEqual(viewscreen_subject(self.ship), 0)
        self.assertFalse(viewscreen_is_live(self.ship))

    def test_set_records_mode_and_subject(self):
        self.assertTrue(viewscreen_set(self.ship, "orbit", self.target))
        self.assertEqual(viewscreen_mode(self.ship), "orbit")
        self.assertEqual(viewscreen_subject(self.ship), self.target)
        self.assertTrue(viewscreen_is_live(self.ship))

    def test_subject_is_stored_as_an_id(self):
        """An object may be handed in; what is kept is the id, so nothing holds a
        reference to something that can be deleted out from under it."""
        viewscreen_set(self.ship, "dolly", to_object(self.target))
        self.assertEqual(viewscreen_subject(self.ship), self.target)

    def test_no_subject_is_zero_not_none(self):
        viewscreen_set(self.ship, "dolly")
        self.assertEqual(viewscreen_subject(self.ship), 0)

    def test_unknown_mode_is_refused_and_changes_nothing(self):
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertFalse(viewscreen_set(self.ship, "spin", self.target))
        self.assertEqual(viewscreen_mode(self.ship), "orbit")

    def test_setting_the_same_shot_twice_is_not_a_change(self):
        self.assertTrue(viewscreen_set(self.ship, "orbit", self.target))
        self.assertFalse(viewscreen_set(self.ship, "orbit", self.target))

    def test_off_is_the_same_as_clear(self):
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertTrue(viewscreen_set(self.ship, "off"))
        self.assertFalse(viewscreen_is_live(self.ship))

    def test_every_mode_is_settable(self):
        for mode in MODES:
            if mode == "off":
                continue
            viewscreen_clear(self.ship)
            self.assertTrue(viewscreen_set(self.ship, mode, self.target), mode)
            self.assertEqual(viewscreen_mode(self.ship), mode)

    # --- what it asks the engine for --------------------------------------
    def test_tactical_asks_for_the_2d_view(self):
        viewscreen_set(self.ship, "tactical", self.target)
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "tactical")

    def test_cinematic_shots_ask_for_the_3d_view(self):
        for mode in ("dolly", "orbit"):
            viewscreen_clear(self.ship)
            set_inventory_value(self.ship, "MAIN_SCREEN_VIEW", "tactical")
            viewscreen_set(self.ship, mode, self.target)
            self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"),
                             "3d_view", mode)

    def test_facing_and_screen_mode_are_left_alone(self):
        """The viewer has an opinion about WHAT is on screen, not about how the crew
        had it framed."""
        set_inventory_value(self.ship, "MAIN_SCREEN_FACING", "left")
        set_inventory_value(self.ship, "MAIN_SCREEN_MODE", "first_person")
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_FACING"), "left")
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_MODE"), "first_person")

    # --- standing down ----------------------------------------------------
    def test_clear_restores_the_view_the_crew_had(self):
        set_inventory_value(self.ship, "MAIN_SCREEN_VIEW", "lrs")
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "3d_view")
        viewscreen_clear(self.ship)
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "lrs")

    def test_shot_to_shot_does_not_overwrite_what_the_crew_had(self):
        """Only the FIRST take records "before" - otherwise standing down restores the
        previous shot's framing, which the crew never chose."""
        set_inventory_value(self.ship, "MAIN_SCREEN_VIEW", "lrs")
        viewscreen_set(self.ship, "orbit", self.target)
        viewscreen_set(self.ship, "tactical", self.target)
        viewscreen_set(self.ship, "dolly", self.target)
        viewscreen_clear(self.ship)
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "lrs")

    def test_clearing_when_off_is_a_no_op(self):
        self.assertFalse(viewscreen_clear(self.ship))

    # --- arbitration with helm --------------------------------------------
    def test_helm_taking_the_screen_stands_the_viewer_down(self):
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertTrue(viewscreen_helm_override(self.ship, "lrs", "front", "long"))
        self.assertFalse(viewscreen_is_live(self.ship))

    def test_helm_override_does_not_restore(self):
        """Helm's choice IS the new state; putting "before" back would undo the change
        being handled."""
        set_inventory_value(self.ship, "MAIN_SCREEN_VIEW", "3d_view")
        viewscreen_set(self.ship, "tactical", self.target)
        viewscreen_helm_override(self.ship, "lrs", "front", "long")
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "lrs")

    def test_a_replay_of_our_own_state_is_not_a_takeover(self):
        """A reconnecting console re-reports the state it is already in."""
        viewscreen_set(self.ship, "orbit", self.target)
        view = get_inventory_value(self.ship, "MAIN_SCREEN_VIEW")
        facing = get_inventory_value(self.ship, "MAIN_SCREEN_FACING", "front")
        mode = get_inventory_value(self.ship, "MAIN_SCREEN_MODE", "chase")
        self.assertFalse(viewscreen_helm_override(self.ship, view, facing, mode))
        self.assertTrue(viewscreen_is_live(self.ship))

    def test_a_facing_change_alone_is_a_takeover(self):
        """Same view, different way round: helm still reached for the control."""
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertTrue(viewscreen_helm_override(self.ship, "3d_view", "aft", "chase"))
        self.assertFalse(viewscreen_is_live(self.ship))

    def test_helm_override_with_no_claim_is_a_no_op(self):
        self.assertFalse(viewscreen_helm_override(self.ship, "lrs", "front", "long"))

    def test_helm_throws_away_a_console_claims_baseline(self):
        """Helm's choice IS the new state, so there is nothing to go back to. A stale
        baseline left recorded would let a later, unrelated release put the screen
        somewhere the crew left minutes ago."""
        from sbs_utils.procedural.gui.viewscreen_claims import viewscreen_baseline
        viewscreen_set(self.ship, "orbit", self.target)
        viewscreen_helm_override(self.ship, "lrs", "front", "long")
        self.assertIsNone(viewscreen_baseline(self.ship))

    # --- the tiers: helm beats a console, a story beats helm ----------------
    def test_helm_does_not_break_a_story_claim(self):
        """A cutscene, a hail, a mission beat. The crew's control is their escape
        hatch from another CONSOLE, not from a directed moment."""
        from sbs_utils.procedural.gui.viewscreen_claims import (TIER_STORY, viewscreen_held,
                                                                viewscreen_tier)
        set_inventory_value(self.ship, "MAIN_SCREEN_VIEW", "3d_view")
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        self.assertFalse(viewscreen_helm_override(self.ship, "lrs", "front", "long"))
        self.assertTrue(viewscreen_is_live(self.ship))
        self.assertEqual(viewscreen_tier(self.ship), TIER_STORY)
        self.assertIsNotNone(viewscreen_held(self.ship), "the crew's press was dropped")

    def test_a_refused_press_does_not_leave_its_view_recorded(self):
        """handlerhooks writes the crew's triple BEFORE asking (issue #595), so the
        refusal has to put the story's own back or the record and the screen
        disagree."""
        from sbs_utils.procedural.gui.viewscreen_claims import TIER_STORY
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        set_inventory_value(self.ship, "MAIN_SCREEN_VIEW", "lrs")   # what handlerhooks does
        viewscreen_helm_override(self.ship, "lrs", "front", "long")
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "3d_view",
                         "the rejected view stayed on the record")

    def test_the_parked_press_applies_when_the_story_releases(self):
        """Honored late, not lost."""
        from sbs_utils.procedural.gui.viewscreen_claims import TIER_STORY
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        viewscreen_helm_override(self.ship, "lrs", "front", "long")
        viewscreen_clear(self.ship, "hail")
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "lrs")
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_FACING"), "front")

    def test_a_console_pick_during_a_story_is_parked_not_applied(self):
        from sbs_utils.procedural.gui.viewscreen_claims import (TIER_STORY, viewscreen_held,
                                                                viewscreen_owner)
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        self.assertFalse(viewscreen_set(self.ship, "tactical", self.target,
                                        owner="science:7"))
        self.assertEqual(viewscreen_mode(self.ship), "orbit")
        self.assertEqual(viewscreen_owner(self.ship), "hail")
        self.assertIsNotNone(viewscreen_held(self.ship))

    def test_the_parked_console_pick_runs_on_release(self):
        from sbs_utils.procedural.gui.viewscreen_claims import (TIER_STORY, viewscreen_owner)
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        viewscreen_set(self.ship, "tactical", self.target, owner="science:7")
        viewscreen_clear(self.ship, "hail")
        self.assertEqual(viewscreen_mode(self.ship), "tactical")
        self.assertEqual(viewscreen_owner(self.ship), "science:7")

    def test_helm_clears_a_parked_console_pick(self):
        """Helm just spoke. A drop-down pick from before that, firing seconds later,
        would override the officer who overrode it."""
        from sbs_utils.procedural.gui.viewscreen_claims import (TIER_STORY, viewscreen_held)
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        viewscreen_set(self.ship, "tactical", self.target, owner="science:7")
        viewscreen_clear(self.ship, "hail")          # the parked pick runs
        self.assertEqual(viewscreen_mode(self.ship), "tactical")
        self.assertTrue(viewscreen_helm_override(self.ship, "lrs", "front", "long"))
        self.assertIsNone(viewscreen_held(self.ship))
        self.assertFalse(viewscreen_is_live(self.ship))

    def test_a_parked_pick_naming_a_dead_subject_is_dropped(self):
        from sbs_utils.procedural.gui.viewscreen_claims import TIER_STORY
        from sbs_utils.procedural.space_objects import delete_object
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        gone = to_id(player_spawn(2000, 0, 0, "Ghost", "tsn", "battle"))
        viewscreen_set(self.ship, "tactical", gone, owner="science:7")
        delete_object(gone)
        viewscreen_clear(self.ship, "hail")
        self.assertFalse(viewscreen_is_live(self.ship),
                         "a shot of a destroyed contact was started anyway")

    # --- flat, last-writer-wins: NOT a stack --------------------------------
    def test_a_story_over_a_console_returns_to_the_crews_view_not_the_console_shot(self):
        """THE assertion most readers will guess wrong. Claims do not stack: when the
        story releases, the screen goes back to what the CREW had, not to whatever
        science had put up before the story took it."""
        set_inventory_value(self.ship, "MAIN_SCREEN_VIEW", "lrs")
        set_inventory_value(self.ship, "MAIN_SCREEN_FACING", "aft")
        from sbs_utils.procedural.gui.viewscreen_claims import TIER_STORY
        viewscreen_set(self.ship, "tactical", self.target, owner="science:7")
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        viewscreen_clear(self.ship, "hail")
        self.assertFalse(viewscreen_is_live(self.ship), "science's shot came back")
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_VIEW"), "lrs")
        self.assertEqual(get_inventory_value(self.ship, "MAIN_SCREEN_FACING"), "aft")

    def test_a_stale_owner_cannot_release_the_screen(self):
        viewscreen_set(self.ship, "orbit", self.target, owner="science:7")
        viewscreen_set(self.ship, "tactical", self.target, owner="weapons:8")
        self.assertFalse(viewscreen_clear(self.ship, "science:7"))
        self.assertEqual(viewscreen_mode(self.ship), "tactical")

    def test_the_effective_state_is_what_the_reroute_must_carry(self):
        """handlerhooks re-stamps the event with this, because the event still holds
        the triple the story refused."""
        from sbs_utils.procedural.gui.viewscreen import viewscreen_effective_state
        from sbs_utils.procedural.gui.viewscreen_claims import TIER_STORY
        viewscreen_set(self.ship, "orbit", self.target, owner="hail", tier=TIER_STORY)
        viewscreen_helm_override(self.ship, "lrs", "front", "long")
        self.assertEqual(viewscreen_effective_state(self.ship)[0], "3d_view")

    # --- scope ------------------------------------------------------------
    def test_two_ships_are_independent(self):
        other = to_id(player_spawn(5000, 0, 0, "Hera", "tsn", "battle"))
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertEqual(viewscreen_mode(other), "off")
        viewscreen_set(other, "tactical", self.ship)
        self.assertEqual(viewscreen_mode(self.ship), "orbit")
        self.assertEqual(viewscreen_subject(other), self.ship)


class TestViewscreenAudience(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.other = to_id(player_spawn(5000, 0, 0, "Hera", "tsn", "battle"))

    def tearDown(self):
        FrameContext.context = None

    def test_only_this_ships_main_screens(self):
        main = _console(C1, self.ship, "console", "mainscreen")
        _console(C2, self.other, "console", "mainscreen")
        self.assertEqual(viewscreen_consoles(self.ship), {main})
        self.assertEqual(viewscreen_consoles(self.other), {C2})

    def test_other_consoles_on_the_same_ship_are_not_the_audience(self):
        main = _console(C1, self.ship, "console", "mainscreen")
        _console(C2, self.ship, "console", "science")
        self.assertEqual(viewscreen_consoles(self.ship), {main})

    def test_no_main_screen_connected_is_empty_not_an_error(self):
        _console(C1, self.ship, "console", "science")
        self.assertEqual(viewscreen_consoles(self.ship), set())


class TestShotLabels(unittest.TestCase):
    """The drop-down contract. Kept in the library so a console's list and the mode
    names cannot drift apart."""

    def test_props_use_the_list_key(self):
        """`items:` is NOT the key. A dropdown without `list:` has nothing to render
        and the engine dies allocating for it - MemoryError: bad allocation, which
        reads as anything but a typo. Found in a browser; caught here now."""
        from sbs_utils.procedural.gui import viewscreen_shot_props
        props = viewscreen_shot_props()
        self.assertIn("list:", props)
        self.assertIn("text:", props)
        self.assertNotIn("items:", props)

    def test_every_label_round_trips_to_its_mode(self):
        from sbs_utils.procedural.gui import (viewscreen_mode_for, viewscreen_label_for,
                                              SHOT_LABELS, viewscreen_shot_props)
        props = viewscreen_shot_props()
        for label, mode in SHOT_LABELS:
            self.assertEqual(viewscreen_mode_for(label), mode)
            self.assertEqual(viewscreen_label_for(mode), label)
            self.assertIn(label, props, "a label the console can pick is not in the list")

    def test_every_label_is_a_real_mode(self):
        from sbs_utils.procedural.gui import SHOT_LABELS
        from sbs_utils.procedural.gui.viewscreen import MODES
        for _label, mode in SHOT_LABELS:
            self.assertIn(mode, MODES)

    def test_an_unknown_label_reads_as_off(self):
        """A console showing something we do not recognize must not leave the main
        screen commandeered."""
        from sbs_utils.procedural.gui import viewscreen_mode_for
        self.assertEqual(viewscreen_mode_for("Warp Nine"), "off")

    def test_labels_are_ascii(self):
        """Engine-rendered strings."""
        from sbs_utils.procedural.gui import SHOT_LABELS
        for label, _mode in SHOT_LABELS:
            label.encode("ascii")


class TestTheConsolesCallSequence(unittest.TestCase):
    """The lines LM's science console actually runs, run here.

    Headless never enters a console page (`gui 0/9`), so nothing else in this suite
    executes the drop-down's code path - and both bugs that reached a browser were in
    exactly these four lines. This is not a GUI test; it is the API contract those
    lines depend on, exercised in their real order.
    """

    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.foe = to_id(player_spawn(3000, 0, 0, "Kraken", "raider", "battle"))
        self.cid = _console(C1, self.ship, "console", "science")
        mock_sbs.assign_client_to_ship(self.cid, self.ship)

    def tearDown(self):
        FrameContext.context = None

    def test_build_then_pick_a_shot(self):
        from sbs_utils.procedural.gui import (viewscreen_home_ship, viewscreen_label_for,
                                              viewscreen_mode, viewscreen_shot_props,
                                              viewscreen_mode_for, viewscreen_set)
        # ---- what the console builds
        sci_ship = viewscreen_home_ship(self.cid)
        self.assertEqual(sci_ship, self.ship)
        on_screen = viewscreen_label_for(viewscreen_mode(sci_ship))
        self.assertEqual(on_screen, "Off")
        props = viewscreen_shot_props(on_screen)
        self.assertIn("list:", props)

        # ---- what the handler does when the player picks one
        on_screen = "On Screen - Orbit"
        ship = viewscreen_home_ship(self.cid)
        self.assertTrue(viewscreen_set(ship, viewscreen_mode_for(on_screen), self.foe))
        self.assertEqual(viewscreen_mode(self.ship), "orbit")
        self.assertEqual(viewscreen_subject(self.ship), self.foe)

        # ---- and a repaint re-selects what is running, rather than showing "Off"
        self.assertEqual(viewscreen_label_for(viewscreen_mode(self.ship)),
                         "On Screen - Orbit")

    def test_picking_off_hands_the_screen_back(self):
        from sbs_utils.procedural.gui import viewscreen_mode_for, viewscreen_set
        viewscreen_set(self.ship, viewscreen_mode_for("On Screen - Dolly"), self.foe)
        viewscreen_set(self.ship, viewscreen_mode_for("Off"), self.foe)
        self.assertFalse(viewscreen_is_live(self.ship))


class TestHandlerWiring(unittest.TestCase):
    """``handlerhooks`` imports the override lazily inside the ``main_screen_change``
    case, so an import cycle would surface only at that moment - in the engine, on a
    helm click. This is the cheap guard against that; it does not exercise the event
    pipeline, which no test in this suite does."""

    def test_the_lazy_import_resolves(self):
        import sbs_utils.handlerhooks           # noqa: F401
        from sbs_utils.procedural.gui.viewscreen import viewscreen_helm_override
        self.assertTrue(callable(viewscreen_helm_override))

    def test_the_gui_package_exports_it(self):
        """MAST reaches these through the gui package, which mast_sbs_procedural
        registers as a whole module of MAST globals."""
        from sbs_utils.procedural.gui import viewscreen_set, viewscreen_consoles
        self.assertTrue(callable(viewscreen_set))
        self.assertTrue(callable(viewscreen_consoles))

    def test_every_public_viewscreen_function_is_exported(self):
        """A viewscreen_* function that is not re-exported is INVISIBLE TO MAST, and
        the failure lands on a console author as `name ... is not defined` at runtime -
        which is exactly how the drop-down's label helper was found, in a browser.
        The package export list is the contract; this is what keeps it complete."""
        import importlib
        import sbs_utils.procedural.gui as gui_pkg
        # importlib, NOT `from ...gui import viewscreen_pages`: a submodule sharing
        # a name with a function the package exports is SHADOWED by it, so that form
        # hands back the FUNCTION and this scan then walks dir(function) and finds
        # nothing. It was passing vacuously for viewscreen_pages exactly that way.
        modules = [importlib.import_module("sbs_utils.procedural.gui." + name)
                   for name in ("viewscreen", "viewscreen_pages", "viewscreen_claims")]
        missing = []
        for module in modules:
            for name in dir(module):
                if not name.startswith("viewscreen_"):
                    continue
                if not callable(getattr(module, name)):
                    continue
                if not hasattr(gui_pkg, name):
                    missing.append(name)
        self.assertEqual(missing, [], f"not exported from procedural.gui: {missing}")


class TestViewscreenShots(unittest.TestCase):
    """Phase 2 - the shots. These drive the mock's `_cinematic` and client-assignment
    state, which is what the engine calls actually set, rather than asserting that our
    own functions were called."""

    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        _VIEWERS.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.target = to_id(player_spawn(4000, 0, 0, "Kraken", "raider", "battle"))
        self.cid = _console(C1, self.ship, "console", "mainscreen")
        mock_sbs.assign_client_to_ship(self.cid, self.ship)

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        _VIEWERS.clear()
        # delete_object() is DEFERRED and ids are RECYCLED, so an undrained queue
        # reaches into the next module and deletes whatever inherited the id.
        DeleteQueue.clear()
        FrameContext.context = None

    def advance(self, seconds):
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1

    # --- who a console belongs to, while a shot has it elsewhere -----------
    def test_camera_assignment_reports_the_home_ship_during_a_shot(self):
        """`camera_assignment` is what a cutscene captures before its first shot so
        it can put the console back afterwards. Reading it off get_ship_of_client
        mid-shot captures the SUBJECT, and camera_restore then dutifully parks the
        main screen on an enemy ship - permanently, because releasing to the engine
        director just keeps it there."""
        from sbs_utils.procedural.gui.camera import camera_assignment
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertEqual(mock_sbs.get_ship_of_client(self.cid), self.target,
                         "precondition: a shot assigns its console to the subject")
        self.assertEqual(camera_assignment([self.cid]).get(self.cid), self.ship)

    def test_a_cutscene_during_a_shot_gives_the_console_its_own_ship_back(self):
        """The reported bug, end to end: a story beat played while science had
        something on screen used to leave the main screen watching that contact
        after the beat ended, with no way for helm to get it back."""
        from sbs_utils.procedural.gui.cutscene import cutscene_play
        viewscreen_set(self.ship, "orbit", self.target)
        prom = cutscene_play([{"subject": self.target, "seconds": 1}], to=[self.cid])
        self.advance(2.0)
        self.assertTrue(prom.done(), "the cutscene never finished")
        self.assertEqual(mock_sbs.get_ship_of_client(self.cid), self.ship,
                         "the console was left riding the cutscene's subject")

    def test_a_cutscene_parks_a_console_pick_and_runs_it_on_release(self):
        """The whole arbitration, through the real cutscene front door: science asks
        for a shot while a story beat is on, and gets it when the beat ends instead
        of being ignored."""
        from sbs_utils.procedural.gui.cutscene import cutscene_play
        from sbs_utils.procedural.gui.viewscreen_claims import viewscreen_owner
        prom = cutscene_play([{"subject": self.target, "seconds": 1}], to=[self.cid])
        self.assertEqual(viewscreen_owner(self.ship), "cutscene")

        self.assertFalse(viewscreen_set(self.ship, "orbit", self.target,
                                        owner="science:%s" % self.cid),
                         "a console pick interrupted a story beat")
        self.assertEqual(viewscreen_mode(self.ship), "off")

        self.advance(2.0)
        self.assertTrue(prom.done())
        self.assertEqual(viewscreen_mode(self.ship), "orbit",
                         "the parked pick never ran")
        self.assertEqual(viewscreen_owner(self.ship), "science:%s" % self.cid)

    # --- the camera -------------------------------------------------------
    def test_a_shot_points_the_camera_at_the_subject(self):
        viewscreen_set(self.ship, "orbit", self.target)
        state = mock_sbs._cinematic.get(self.cid)
        self.assertIsNotNone(state, "no camera was set")
        self.assertEqual(state["dolly_id"], self.target)

    def test_tactical_is_not_a_camera_move(self):
        """It still gets a viewer record - the data column needs one - but no camera."""
        viewscreen_set(self.ship, "tactical", self.target)
        self.assertIsNone(_VIEWERS[self.ship]["prom"])
        self.assertEqual(mock_sbs._cinematic, {})
        self.assertEqual(mock_sbs.sim.client_alt_ships.get(self.cid), self.target)

    def test_standing_down_clears_the_2d_focus(self):
        viewscreen_set(self.ship, "tactical", self.target)
        viewscreen_clear(self.ship)
        self.assertIsNone(mock_sbs.sim.client_alt_ships.get(self.cid))

    def test_no_console_means_no_shot(self):
        other = to_id(player_spawn(9000, 0, 0, "Hera", "tsn", "battle"))
        viewscreen_set(other, "orbit", self.target)
        self.assertEqual(len(_VIEWERS), 0)

    # --- the assignment, which is the thing to know -----------------------
    def test_the_console_is_assigned_to_the_subject_while_a_shot_runs(self):
        """The engine only honors a camera change when the console is assigned to the
        object the lens rides, so a shot moves the assignment. This is not incidental -
        it is why viewscreen_home_ship exists."""
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertEqual(mock_sbs.sim.client_ships[self.cid], self.target)

    def test_home_ship_still_answers_with_the_consoles_own_ship(self):
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertEqual(mock_sbs.get_ship_of_client(self.cid), self.target)
        self.assertEqual(viewscreen_home_ship(self.cid), self.ship)

    def test_standing_down_gives_the_console_its_ship_back(self):
        viewscreen_set(self.ship, "orbit", self.target)
        viewscreen_clear(self.ship)
        self.assertEqual(mock_sbs.sim.client_ships[self.cid], self.ship)
        self.assertEqual(viewscreen_home_ship(self.cid), self.ship)

    def test_home_is_recorded_once_not_per_shot(self):
        """Recording it again while a shot is running would save the SUBJECT as home,
        and standing down would strand the console on someone else's ship."""
        viewscreen_set(self.ship, "orbit", self.target)
        viewscreen_set(self.ship, "dolly", self.target)
        viewscreen_clear(self.ship)
        self.assertEqual(mock_sbs.sim.client_ships[self.cid], self.ship)

    # --- framing ----------------------------------------------------------
    def test_framing_scales_with_the_hull(self):
        small = viewscreen_framing(self.target)
        to_object(self.target).space_object().exclusion_radius = 2000.0
        big = viewscreen_framing(self.target)
        self.assertGreater(big[0], small[0])
        self.assertGreater(big[1], small[1])

    def test_framing_never_goes_inside_the_floor(self):
        to_object(self.target).space_object().exclusion_radius = 1.0
        near, far = viewscreen_framing(self.target)
        self.assertGreaterEqual(near, 250.0)
        self.assertGreater(far, near)

    def test_framing_of_nothing_still_returns_a_usable_shot(self):
        near, far = viewscreen_framing(0)
        self.assertGreater(near, 0)
        self.assertGreater(far, near)

    # --- the loop ---------------------------------------------------------
    def test_the_dolly_ping_pongs_instead_of_cutting_back(self):
        """A push that jumped back to wide every leg would read as a cut."""
        viewscreen_set(self.ship, "dolly", self.target)
        self.assertEqual(_VIEWERS[self.ship]["leg"], 1)
        self.advance(24.0)
        self.assertGreater(_VIEWERS[self.ship]["leg"], 1, "the loop did not continue")

    def test_the_orbit_carries_its_angle_over(self):
        viewscreen_set(self.ship, "orbit", self.target)
        first = _VIEWERS[self.ship]["yaw"]
        self.advance(50.0)
        self.assertGreater(_VIEWERS[self.ship]["leg"], 1)
        self.assertEqual(_VIEWERS[self.ship]["yaw"], first)   # 360 back to where it was

    def test_the_shot_ends_when_its_subject_does(self):
        viewscreen_set(self.ship, "orbit", self.target)
        delete_object(self.target)
        self.advance(2.0)
        self.assertFalse(viewscreen_is_live(self.ship),
                         "the viewer held the screen on a dead id")
        self.assertEqual(len(_VIEWERS), 0)

    # --- the reset ledger -------------------------------------------------
    def test_reset_empties_the_records(self):
        viewscreen_set(self.ship, "orbit", self.target)
        self.assertEqual(len(_VIEWERS), 1)
        viewscreen_reset()
        self.assertEqual(len(_VIEWERS), 0)

    def test_the_container_is_declared_to_the_reset_audit(self):
        """An unregistered module-level container is invisible to the restart soak -
        exactly the run-2 bug the ledger exists to catch."""
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("viewscreen shots", _RESET_PROBES)


if __name__ == "__main__":
    unittest.main()
