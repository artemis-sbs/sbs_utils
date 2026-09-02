"""Re-hulling a player ship after spawn must re-derive its stats.

`SpaceObject.set_ship_data_key` writes `data_tag` and tells the clients, and that is
all it does - while the engine derives shields, beams, tubes and turn rate from shipData
at CREATION. So a ship given a new hull minutes after spawn kept the previous hull's
numbers, with nothing logged.

Reported from the Gamma with a Q playtest, 2026-09-01: "player ships only change the
art". Every trial there calls `q_cast_take_command`, which set the hull key and nothing
else, so a Defiant flew with whatever the roster seated the crew in.

`player_ship_rebuild_stats` is the roster's own re-hull path (`player_roster_apply`),
factored out so there is one of it rather than two.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock


class PlayerHullRebuildTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        from sbs_utils.helpers import FrameContext, Context
        FrameContext.context = Context(self.sim, sbs, None)

    def _two_hulls_that_differ(self, field="turn_rate"):
        """Two shipData keys whose `field` is not the same, so the assertions mean
        something. Picked from the live table rather than hard-coded, because a stock
        data file is free to retune any single hull."""
        from sbs_utils.procedural.ship_data import get_ship_data_for
        keys = ("tsn_light_cruiser", "tsn_battle_cruiser", "tsn_scout",
                "tsn_dreadnought", "tsn_missile_cruiser")
        seen = []
        for k in keys:
            d = get_ship_data_for(k)
            if d is not None and d.get(field) is not None:
                seen.append((k, float(d.get(field))))
        for i in range(len(seen)):
            for j in range(i + 1, len(seen)):
                if seen[i][1] != seen[j][1]:
                    return seen[i], seen[j]
        self.skipTest("no two stock hulls differ on %s in this shipData" % field)

    def test_setting_the_hull_alone_does_not_move_the_stats(self):
        """The behavior being worked around - pinned so it is documented rather than
        rediscovered. `set_ship_data_key` is an ART call."""
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_object, to_id
        (key_a, val_a), (key_b, val_b) = self._two_hulls_that_differ()

        p = to_object(to_id(player_spawn(0, 0, 0, "Artemis", "tsn", key_a)))
        self.assertAlmostEqual(p.data_set.get("turn_rate", 0), val_a, places=5)

        p.set_ship_data_key(key_b)
        self.assertAlmostEqual(p.data_set.get("turn_rate", 0), val_a, places=5,
                               msg="the hull key alone must not be expected to retune")

    def test_the_rebuild_brings_the_new_hulls_stats(self):
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_object, to_id
        from sbs_utils.procedural.player_roster import player_ship_rebuild_stats
        (key_a, val_a), (key_b, val_b) = self._two_hulls_that_differ()

        p = to_object(to_id(player_spawn(0, 0, 0, "Artemis", "tsn", key_a)))
        p.set_ship_data_key(key_b)

        self.assertTrue(player_ship_rebuild_stats(p))
        self.assertAlmostEqual(p.data_set.get("turn_rate", 0), val_b, places=5,
                               msg="stats must follow the hull")

    def test_the_cached_blob_still_points_at_the_live_one(self):
        """The rebuild REPLACES the blob, and `SpaceObject._data_set` is captured once
        at spawn. Without the re-read the agent keeps handing out the pre-rebuild handle
        while `_alive` stays True, so every later write lands in the dead one."""
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_object, to_id
        from sbs_utils.procedural.player_roster import player_ship_rebuild_stats
        (key_a, _), (key_b, _) = self._two_hulls_that_differ()

        p = to_object(to_id(player_spawn(0, 0, 0, "Artemis", "tsn", key_a)))
        p.set_ship_data_key(key_b)
        player_ship_rebuild_stats(p)

        p.data_set.set("a_probe_value", 17, 0)
        self.assertEqual(p.engine_object.data_set.get("a_probe_value", 0), 17,
                         "the agent's blob and the engine's must be the same object")

    def test_it_is_safe_on_an_agent_with_no_engine_object(self):
        """Best-effort by design - a rebuild must never be the thing that breaks its
        caller."""
        from sbs_utils.procedural.player_roster import player_ship_rebuild_stats

        class _Bare:
            engine_object = None

        self.assertFalse(player_ship_rebuild_stats(_Bare()))


if __name__ == "__main__":
    unittest.main()
