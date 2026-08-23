"""Changing a ship's hull announces itself, because the INTERIOR does not follow it.

WHY THIS EXISTS. ``grid_rebuild_grid_objects`` has no caller inside sbs_utils - every
one is a mission. LegendaryMissions builds a ship's engineering grid from a ``//spawn``
route that waits one sim-second ("ship type could be changed by helm") and then never
runs again. That grace covers the setup screen. It does not cover a hull changed later.

When the hull changes the engine re-sizes the ship's internal map, but the grid objects
standing in it are the old hull's, so Engineering goes blank or wrong - and nothing is
logged, because nothing noticed. Found on Cosmos-TNG-Missions, where all 8 trial maps
seat the crew in a story hull minutes after spawn.

``set_ship_data_key`` is the single funnel every hull change passes through, so it is
where the notification belongs. It EMITS rather than rebuilding: a rebuild deletes and
respawns 60-100 grid objects, which is far too heavy to hide in a property setter, and
the library has no other dependency on that function.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  - settles the comms import order
from cosmos_dev.mock import sbs
from sbs_utils.helpers import Context, FrameContext, FakeEvent
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.signal import signal_observe, signal_unobserve
from sbs_utils.spaceobject import SpaceObject


class TestHullChangeSignal(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.seen = []
        signal_observe(self._watch)
        self.addCleanup(signal_unobserve, self._watch)
        # npc_spawn hands back a SpawnData wrapper; the SpaceObject is `py_object`.
        self.ship = npc_spawn(0, 0, 0, "Probe", "tsn", "tsn_light_cruiser",
                              "behav_npcship").py_object

    def _watch(self, name, data):
        if name == "ship_hull_changed":
            self.seen.append(data)

    def test_a_real_change_is_announced(self):
        self.ship.set_ship_data_key("tsn_battleship")
        self.assertEqual(len(self.seen), 1)
        d = self.seen[0]
        # CAPS keys: the convention reserves that spelling for system-emitted signals,
        # and they arrive as task variables in the handler.
        self.assertEqual(d["SHIP_ID"], self.ship.id)
        self.assertEqual(d["HULL_OLD_KEY"], "tsn_light_cruiser")
        self.assertEqual(d["HULL_NEW_KEY"], "tsn_battleship")

    def test_setting_the_same_key_is_not_a_change(self):
        # Cloak/uncloak loops and roster reconciliation both re-assert the current hull
        # every pass. Announcing those would rebuild the grid for nothing.
        self.ship.set_ship_data_key("tsn_light_cruiser")
        self.assertEqual(self.seen, [])

    def test_the_deprecated_setter_announces_too(self):
        # set_art_id delegates rather than repeating the body, so there is exactly ONE
        # funnel. It is still the spelling LegendaryMissions' cloak uses.
        self.ship.set_art_id("tsn_battleship")
        self.assertEqual(len(self.seen), 1)
        self.assertEqual(self.seen[0]["HULL_NEW_KEY"], "tsn_battleship")

    def test_the_key_is_actually_applied(self):
        # The notification must not become the point of the function.
        self.ship.set_ship_data_key("tsn_battleship")
        self.assertEqual(self.ship.ship_data_key, "tsn_battleship")

    def test_a_broken_listener_cannot_break_the_hull_change(self):
        def boom(name, data):
            raise RuntimeError("listener is broken")
        signal_observe(boom)
        self.addCleanup(signal_unobserve, boom)
        self.ship.set_ship_data_key("tsn_battleship")
        self.assertEqual(self.ship.ship_data_key, "tsn_battleship")


if __name__ == "__main__":
    unittest.main()
