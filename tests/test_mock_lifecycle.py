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
