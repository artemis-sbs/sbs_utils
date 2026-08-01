"""stop_dist must reach the physics layer, not just the calling tick.

target()/target_pos() evaluate stop_dist ONCE, when the brain calls them, and act on
it by zeroing throttle. That alone makes the stand-off distance a function of the
brain's tick rate rather than of the distance: between calls nothing holds the ship
back. cosmos_dev's mock physics reads data_set "stop_dist" every tick to brake and
park, but nothing had ever written that key -- so every NPC fell through to the 20u
default and closed to ramming range regardless of what its brain asked for.
"""
from cosmos_dev.mock import sbs as sbs
import math
import unittest

from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.space_objects import target, target_pos
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.helpers import FrameContext, Context, FakeEvent

test_set_exe_dir()


class TestTargetStopDist(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _pair(self):
        prey = npc_spawn(0, 0, 0, "Prey", "tsn", "tsn_battle_cruiser", "behav_npcship")
        hunter = npc_spawn(0, 0, -4000, "Hunter", "torgoth", "torgoth_destroyer",
                           "behav_npcship")
        return hunter, prey

    def _separation(self, a, b):
        oa = sbs.sim.space_objects[a.id]
        ob = sbs.sim.space_objects[b.id]
        return math.dist((oa._pos.x, oa._pos.y, oa._pos.z),
                         (ob._pos.x, ob._pos.y, ob._pos.z))

    def _settle(self, seconds=90):
        for _ in range(int(30 * seconds)):
            sbs.physics_tick(1.0 / 30.0)

    def test_target_stores_stop_dist(self):
        hunter, prey = self._pair()
        target(hunter.id, prey.id, True, 1.0, stop_dist=900)
        self.assertEqual(sbs.sim.space_objects[hunter.id].data_set.get("stop_dist"), 900,
                         "stop_dist must be persisted so the physics can hold station")

    def test_target_pos_stores_stop_dist(self):
        hunter, _ = self._pair()
        target_pos(hunter.id, 0, 0, 0, 1.0, stop_dist=750)
        self.assertEqual(sbs.sim.space_objects[hunter.id].data_set.get("stop_dist"), 750)

    def test_unset_stop_dist_stores_zero(self):
        """None must not write a stand-off - the physics falls back to its own default."""
        hunter, prey = self._pair()
        target(hunter.id, prey.id, True, 1.0)
        self.assertEqual(sbs.sim.space_objects[hunter.id].data_set.get("stop_dist"), 0)

    def test_hunter_holds_station_at_stop_dist(self):
        hunter, prey = self._pair()
        sbs.resume_sim()
        target(hunter.id, prey.id, True, 1.0, stop_dist=900)
        self._settle()
        sep = self._separation(hunter, prey)
        # Brake lag leaves it a little inside; what matters is it parks near 900, not 20.
        self.assertGreater(sep, 700, f"hunter closed to {sep:.0f}u despite stop_dist=900")
        self.assertLess(sep, 1100, f"hunter stalled at {sep:.0f}u, well outside stop_dist=900")

    def test_larger_stop_dist_parks_further_out(self):
        hunter, prey = self._pair()
        sbs.resume_sim()
        target(hunter.id, prey.id, True, 1.0, stop_dist=2500)
        self._settle()
        sep = self._separation(hunter, prey)
        self.assertGreater(sep, 2200, f"hunter closed to {sep:.0f}u despite stop_dist=2500")


if __name__ == "__main__":
    unittest.main()
