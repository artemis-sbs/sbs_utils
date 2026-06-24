"""Regression tests for mock mission-lifecycle / fidelity fixes:

* physics_tick is the sim-time source (advances time_tick_counter at TPS,
  drift-free, frozen while paused)
* settings.yaml is loaded relative to fs.script_dir (the mission folder)
* mockgui.create_new_sim() emits a world_reset and stops the previous
  mission's 2D radar rect from being re-registered
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import queue as _queue
import tempfile
import unittest

import cosmos_dev.mock.sbs as base
import cosmos_dev.mockgui.sbs as mockgui
from sbs_utils import fs
from sbs_utils.helpers import _TPS
import sbs_utils.procedural.settings as settings_mod


class TestPhysicsSimTime(unittest.TestCase):
    """time_tick_counter must advance from the physics tick, drift-free."""

    def setUp(self):
        base.create_new_sim()
        base.resume_sim()

    def test_tick_advances_counter_by_dt_times_tps(self):
        start = base.sim.time_tick_counter
        base.physics_tick(dt=0.5)
        self.assertEqual(base.sim.time_tick_counter - start, round(0.5 * _TPS))

    def test_one_sim_second_per_second_at_30hz(self):
        start = base.sim.time_tick_counter
        for _ in range(30):
            base.physics_tick(dt=1 / 30)
        self.assertEqual(base.sim.time_tick_counter - start, 30)

    def test_no_drift_at_non_divisor_rate(self):
        # dt=1/16 -> 1.875 ticks each; the fractional accumulator must keep it exact.
        start = base.sim.time_tick_counter
        for _ in range(16):
            base.physics_tick(dt=1 / 16)
        self.assertEqual(base.sim.time_tick_counter - start, 30)   # exactly 1 sim-second

    def test_paused_sim_does_not_advance(self):
        base.sim._paused = True
        start = base.sim.time_tick_counter
        base.physics_tick(dt=0.5)
        self.assertEqual(base.sim.time_tick_counter, start)

    def test_app_seconds_does_not_advance_sim_time(self):
        start = base.sim.time_tick_counter
        base.app_seconds()
        base.app_seconds()
        self.assertEqual(base.sim.time_tick_counter, start)


class TestSettingsPath(unittest.TestCase):
    """settings_get_defaults must load settings.yaml from the mission dir
    (fs.script_dir), so missions in the mock honour their settings."""

    def setUp(self):
        self._saved_script_dir = fs.script_dir
        self._saved_cache = settings_mod.setting_defaults
        self._tmp = tempfile.mkdtemp()
        fs.script_dir = self._tmp
        settings_mod.setting_defaults = None   # bust the module cache

    def tearDown(self):
        fs.script_dir = self._saved_script_dir
        settings_mod.setting_defaults = self._saved_cache

    def test_yaml_values_override_builtin_defaults(self):
        with open(os.path.join(self._tmp, "settings.yaml"), "w") as f:
            f.write("DIFFICULTY: 9\nAUTO_PLAY:\n    enable: true\n")
        s = settings_mod.settings_get_defaults()
        self.assertEqual(s["DIFFICULTY"], 9)                  # overrode builtin 5
        self.assertEqual(s["AUTO_PLAY"]["enable"], True)

    def test_missing_yaml_falls_back_to_builtin(self):
        # No settings.yaml in the mission dir -> builtin defaults only.
        s = settings_mod.settings_get_defaults()
        self.assertEqual(s["DIFFICULTY"], 5)
        self.assertNotIn("AUTO_PLAY", s)   # only the autoplay addon adds this default


class TestWorldResetOnSimCreate(unittest.TestCase):
    """create_new_sim() must wipe the previous mission's view state."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()

    def _drain(self):
        items = []
        while not mockgui.gui_queue.empty():
            items.append(mockgui.gui_queue.get_nowait())
        return items

    def test_create_new_sim_emits_world_reset(self):
        mockgui.create_new_sim()
        cmds = [m.get("cmd") for m in self._drain()]
        self.assertIn("world_reset", cmds)

    def test_create_new_sim_clears_2d_view_tracking(self):
        # Simulate a previous mission having registered a 2D radar view.
        mockgui._view2d_widget_clients[5] = "2dview"
        mockgui._explicit_2d_rects[5] = {"2dview"}
        mockgui.create_new_sim()
        self.assertEqual(mockgui._view2d_widget_clients, {})
        self.assertEqual(mockgui._explicit_2d_rects, {})

    def test_no_emit_when_queue_unset(self):
        # Startup path: create_new_sim before the server/queue exists must not raise.
        mockgui.gui_queue = None
        mockgui.create_new_sim()   # must be a no-op, not an error


class TestCreateNewSimIdentity(unittest.TestCase):
    """create_new_sim must reset IN PLACE (same object), so a reference taken
    before a script's sim_create() (e.g. the in-flight FrameContext.context.sim)
    stays valid - otherwise objects spawned after sim_create land on an orphaned
    instance and their ids get reused on the new one (the 'player is a starbase'
    bug)."""

    def test_resets_in_place_preserving_identity(self):
        s1 = base.create_new_sim()
        s1.create_space_object("behav_playership", "tsn_light_cruiser", 0x20)
        self.assertEqual(len(s1.space_objects), 1)
        s2 = base.create_new_sim()
        self.assertIs(s1, s2)                                   # same object
        self.assertEqual(len(s2.space_objects), 0)             # state cleared
        self.assertEqual(s2.object_ids, 0x4000000000000000)    # id counter reset

    def test_objects_after_reset_do_not_collide_with_stale_refs(self):
        base.create_new_sim()
        held = base.sim                       # reference taken before sim_create()
        base.create_new_sim()                 # script calls sim_create()
        new_id = base.sim.create_space_object("behav_station", "starbase", 0x10)
        # The held reference sees the same object, so the new id is visible there.
        self.assertIs(held, base.sim)
        self.assertIn(new_id, held.space_objects)


class TestDetectGameEnd(unittest.TestCase):
    """_detect_game_end reads Agent.SHARED + the registered end conditions to
    report win/lose - the harness's game-end test surface."""

    def setUp(self):
        from sbs_utils.agent import Agent
        import sbs_utils.procedural.objective as obj
        Agent.clear()
        self._saved = getattr(obj, "__end_game_promise", [])

    def tearDown(self):
        from sbs_utils.agent import Agent
        import sbs_utils.procedural.objective as obj
        setattr(obj, "__end_game_promise", self._saved)
        Agent.clear()

    def _set_end(self, message, is_win):
        from sbs_utils.agent import Agent
        import sbs_utils.procedural.objective as obj

        class _DonePromise:
            def done(self_):
                return True

        Agent.SHARED.set_inventory_value("GAME_ENDED", True)
        Agent.SHARED.set_inventory_value("START_TEXT", message)
        setattr(obj, "__end_game_promise",
                [(0, _DonePromise(), message, is_win, None, None)])

    def test_none_when_not_ended(self):
        from cosmos_dev.mission_runner import _detect_game_end
        self.assertIsNone(_detect_game_end(None))

    def test_reports_win(self):
        from cosmos_dev.mission_runner import _detect_game_end
        self._set_end("Mission complete!", True)
        self.assertEqual(_detect_game_end(None), ("Mission complete!", True))

    def test_reports_lose(self):
        from cosmos_dev.mission_runner import _detect_game_end
        self._set_end("All ships destroyed.", False)
        self.assertEqual(_detect_game_end(None), ("All ships destroyed.", False))


class TestGetShipOfClientFallback(unittest.TestCase):
    """get_ship_of_client mirrors the engine: an unassigned client grabs a
    PLAYER-abit ship, and deleting a ship falls over to another player ship."""

    PLAYER = 0x20
    NPC = 0x10

    def setUp(self):
        base.create_new_sim()

    def _spawn(self, abits):
        return base.sim.create_space_object("behav_x", "hull", abits)

    def test_unassigned_client_grabs_player_ship(self):
        self._spawn(self.NPC)                 # not a player ship - must be skipped
        pid = self._spawn(self.PLAYER)
        self.assertEqual(base.get_ship_of_client(0), pid)
        # the grab is recorded (engine "grabs" and assigns)
        self.assertEqual(base.sim.client_ships.get(0), pid)

    def test_no_player_ship_returns_zero(self):
        self._spawn(self.NPC)
        self.assertEqual(base.get_ship_of_client(0), 0)

    def test_prefers_ship_not_claimed_by_another_client(self):
        p1 = self._spawn(self.PLAYER)
        p2 = self._spawn(self.PLAYER)
        base.assign_client_to_ship(1, p1)     # client 1 owns p1
        self.assertEqual(base.get_ship_of_client(0), p2)   # client 0 takes the free one

    def test_explicit_assignment_is_returned_as_is(self):
        # A ship that isn't a mock space object (bare assignment) must still be
        # honoured - the fallback only triggers on an empty assignment.
        base.assign_client_to_ship(0, 0xABC)
        self.assertEqual(base.get_ship_of_client(0), 0xABC)

    def test_deleting_assigned_ship_falls_over(self):
        p1 = self._spawn(self.PLAYER)
        p2 = self._spawn(self.PLAYER)
        self.assertEqual(base.get_ship_of_client(0), p1)   # grabs p1
        base.delete_object(p1)                             # p1 destroyed
        self.assertEqual(base.get_ship_of_client(0), p2)   # falls over to p2
