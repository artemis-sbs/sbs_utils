"""The reset ledger: nothing survives a mission restart that shouldn't.

Cosmos forks a fresh Python process per mission, so the engine never carries
per-mission state across a restart. The dev runner REUSES the interpreter, so
every module-level container that nobody clears becomes a "works on run 1,
broken on run 2" bug - and those are expensive precisely because run 1 looks fine.

reset_mission_state() is the single source of truth for the reset; the ledger
(register_reset_state / reset_mission_audit) is how a container declares that it
takes part. A new global that forgets to register is invisible to this test; a
registered one that forgets to clear FAILS it, which is the whole point.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import queue as _queue
import unittest

import cosmos_dev.mock.sbs as _base_mock
import cosmos_dev.mockgui.sbs as mockgui
from sbs_utils.procedural.roles import add_role
from sbs_utils.handlerhooks import (register_reset_state, reset_mission_audit,
                                    reset_mission_state, _RESET_PROBES)
from tests.reset_helper import reset_mock


class TestResetLedger(unittest.TestCase):
    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        reset_mock(mockgui)

    def test_ledger_covers_the_known_leak_sites(self):
        """Every container a past run-2 bug came from is declared."""
        for name in ("Agent.all", "Gui.clients", "TickDispatcher",
                     "mock.hull_map_objects", "mock.space_objects",
                     "mock.active_ids", "mockgui.last_per_ship",
                     "mockgui.hud_cache",
                     # AMD CONTENT read out of a mission's .amd. Both were
                     # module-level, uncleared and unregistered: overlay records
                     # let run 2 resolve a key only run 1 declared, and the quest
                     # console set was add-only across a reload.
                     "amd overlays", "quest consoles"):
            self.assertIn(name, _RESET_PROBES, f"{name} is not in the reset ledger")

    def test_clean_after_reset(self):
        self.assertEqual(reset_mission_audit(), {},
                         "state survived a reset with nothing running")

    def test_a_populated_world_leaves_nothing_behind(self):
        """Build a world, restart, and demand a clean slate."""
        for i in range(4):
            oid = _base_mock.sim.create_space_object("behav_npcship", "raider", 0x10)
            obj = _base_mock.sim.space_objects[oid]
            obj._side = "raider"
            obj._pos = _base_mock.vec3(100.0 * i, 0.0, 100.0)
            add_role(oid, "enemy")
        _base_mock.sim.add_navpoint(0, 0, 0, "rally", "")
        mockgui._push_radar()                      # populates the delta baselines
        self.assertNotEqual(reset_mission_audit(), {}, "the world did not populate anything")

        reset_mission_state()
        mockgui.create_new_sim()

        leaks = reset_mission_audit()
        self.assertEqual(leaks, {},
                         f"these survived the restart and would corrupt run 2: {leaks}")

    def test_a_forgotten_container_is_reported(self):
        """The ledger's own failure mode: a registered container nobody clears."""
        never_cleared = {"stale": 1}
        register_reset_state("test.never_cleared", lambda: len(never_cleared))
        try:
            reset_mission_state()
            mockgui.create_new_sim()
            self.assertIn("test.never_cleared", reset_mission_audit())
        finally:
            _RESET_PROBES.pop("test.never_cleared", None)


if __name__ == "__main__":
    unittest.main()
