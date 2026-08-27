"""Mod-merged ship and interior data must not survive a mission restart.

`ship_data_cache` and `_grid_data`/`_grid_theme` look like read-only caches of engine
files. They are not: each is the base table MERGED with what the mission added - its
`extraShipData`, its `extra_grid_data.json`, and (once mods can contribute) every mod it
enabled. That makes them per-mission state wearing the clothes of a cache.

Nothing cleared them. The engine forks a fresh process per mission so it never noticed;
`cosmos_dev` reuses one interpreter, so mission B silently inherited mission A's ships
and interiors. Harmless while no mission merges anything - a correctness bug the moment
mods exist, which is why this is fixed before the mod API rather than after.

The trap this guards against: `reset_ship_data_caches()` clears only the DERIVED caches
and is called BY the merge functions, so it must never drop the merged list. The
mission-boundary reset is a separate function, and `test_merge_survives_its_own_cache_reset`
is what stops the two being collapsed back together.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.ship_data import EXTRA_SHIP_DATA_DISABLED

from sbs_utils.handlerhooks import (reset_mission_audit, reset_mission_state,
                                    _RESET_PROBES)
from sbs_utils.procedural import ship_data as sd
from sbs_utils.procedural import grid as g


_MOD_YAML = """
'#ship-list':
  - key: test_mod_raider
    name: Test Mod Raider
    side: pirate
    artfileroot: pirate_longbow
"""


class TestModDataDoesNotSurviveRestart(unittest.TestCase):
    def tearDown(self):
        # Never leave merged test entries behind for another test file.
        sd.ship_data_reset_for_mission()
        g.grid_reset_caches()

    def test_registered_in_the_ledger(self):
        for name in ("ship_data_cache", "grid_data", "grid_theme",
                     "grid_theme_current"):
            self.assertIn(name, _RESET_PROBES,
                          f"{name} is not in the reset ledger")

    @unittest.skipIf(EXTRA_SHIP_DATA_DISABLED,
                     "extra ship data is off (HOT FIX 2026-08-27)")
    def test_merged_mod_ships_do_not_survive(self):
        sd.merge_mod_ship_yaml(_MOD_YAML, "TestMod")
        self.assertIsNotNone(sd.get_ship_data_for("test_mod_raider"),
                             "the mod ship did not merge, so the test proves nothing")

        reset_mission_state()

        self.assertEqual(sd.ship_data_is_loaded(), 0,
                         "ship data survived the restart")
        self.assertIsNone(sd.ship_data_cache)

    @unittest.skipIf(EXTRA_SHIP_DATA_DISABLED,
                     "extra ship data is off (HOT FIX 2026-08-27)")
    def test_merge_survives_its_own_cache_reset(self):
        """The trap: merge_mod_ship_yaml calls reset_ship_data_caches() itself.

        If that ever also cleared ship_data_cache, every merge would silently throw away
        the entries it had just added.
        """
        sd.merge_mod_ship_yaml(_MOD_YAML, "TestMod")
        sd.reset_ship_data_caches()
        self.assertIsNotNone(sd.get_ship_data_for("test_mod_raider"),
                             "reset_ship_data_caches() dropped the merged entries")

    def test_grid_data_and_theme_do_not_survive(self):
        g.grid_get_grid_data()
        g.grid_get_grid_theme()
        self.assertEqual(g.grid_data_is_loaded(), 1,
                         "grid data did not load, so the test proves nothing")

        reset_mission_state()

        self.assertEqual(g.grid_data_is_loaded(), 0, "grid data survived the restart")
        self.assertEqual(g.grid_theme_is_loaded(), 0, "grid theme survived the restart")

    def test_selected_theme_returns_to_default(self):
        """A per-mission SETTING, not a container - and the kind that fails silently.

        Carried over, the next mission is re-skinned with no error to show for it.
        """
        g.grid_get_grid_theme()
        g.grid_set_grid_current_theme(1)
        self.assertEqual(g.grid_theme_current_index(), 1,
                         "the theme did not change, so the test proves nothing")

        reset_mission_state()

        self.assertEqual(g.grid_theme_current_index(), 0,
                         "the selected theme survived the restart")

    @unittest.skipIf(EXTRA_SHIP_DATA_DISABLED,
                     "extra ship data is off (HOT FIX 2026-08-27)")
    def test_audit_reports_them_by_name(self):
        """A leak has to be REPORTED, not just fixed - that is what the ledger is for."""
        sd.merge_mod_ship_yaml(_MOD_YAML, "TestMod")
        g.grid_get_grid_data()

        audit = reset_mission_audit()
        self.assertIn("ship_data_cache", audit)
        self.assertIn("grid_data", audit)

        reset_mission_state()

        audit = reset_mission_audit()
        self.assertNotIn("ship_data_cache", audit)
        self.assertNotIn("grid_data", audit)


if __name__ == "__main__":
    unittest.main()
