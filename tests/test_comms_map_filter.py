"""The comms map filter and extra scan sources: engine data sets the script clears and
rewrites.

`comms_map_filter` on a player ship lists the ids its comms 2D map shows (empty = all).
`extra_scan_source` lists what else the ship sees through. Both are written as indices
0..n-1, so both must be cleared first or a shorter list leaves the old tail behind.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes            # noqa: F401  breaks a circular import
from cosmos_dev.mock import sbs
from sbs_utils.agent import clear_shared
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural.comms import (comms_map_filter_set, comms_map_filter_clear,
                                        comms_map_filter_get)
from sbs_utils.procedural.extra_scan_sources import extra_scan_sources_run_all
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.links import link, unlink
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.spaceobject import SpaceObject


class Base(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        DeleteQueue.clear()
        clear_shared()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0))
        self.ship = to_id(player_spawn(0, 0, 0, "Hero", "tsn", "tsn_light_cruiser"))
        self.a = to_id(npc_spawn(1000, 0, 0, "A", "tsn", "tsn_light_cruiser", "behav_npcship"))
        self.b = to_id(npc_spawn(2000, 0, 0, "B", "tsn", "tsn_light_cruiser", "behav_npcship"))
        self.c = to_id(npc_spawn(3000, 0, 0, "C", "tsn", "tsn_light_cruiser", "behav_npcship"))
        self.ds = sbs.sim.get_space_object(self.ship).data_set

    def tearDown(self):
        FrameContext.context = None

    def written(self, tag="comms_map_filter"):
        return [self.ds.get(tag, i) for i in range(self.ds.num_elements(tag))]


class TestCommsMapFilter(Base):

    def test_WRITES_THE_IDS_AFTER_A_CLEAR(self):
        comms_map_filter_set(self.ship, [self.c, self.a])
        self.assertEqual(sorted([self.a, self.c]), self.written())

    def test_A_SHORTER_LIST_LEAVES_NO_TAIL(self):
        comms_map_filter_set(self.ship, [self.a, self.b, self.c])
        comms_map_filter_set(self.ship, [self.b])
        self.assertEqual([self.b], self.written())

    def test_ONLY_ENGINE_SPACE_OBJECTS_ARE_WRITTEN(self):
        person = lifeform_spawn("Ensign", "", "crew")
        dead = self.c
        delete_object(dead)
        comms_map_filter_set(self.ship, [self.a, person, dead, 0, None])
        self.assertEqual([self.a], self.written())

    def test_AN_EMPTY_LENS_WRITES_THE_SHIP_NOT_NOTHING(self):
        """Empty means "show everything" to the engine."""
        comms_map_filter_set(self.ship, [])
        self.assertEqual([self.ship], self.written())

    def test_clear_empties_it(self):
        comms_map_filter_set(self.ship, [self.a])
        comms_map_filter_clear(self.ship)
        self.assertEqual([], self.written())
        self.assertEqual([], comms_map_filter_get(self.ship))

    def test_an_unchanged_set_is_not_resent(self):
        comms_map_filter_set(self.ship, [self.a, self.b])
        gen = self.ds.gen
        comms_map_filter_set(self.ship, [self.b, self.a])
        self.assertEqual(gen, self.ds.gen)

    def test_set_after_clear_writes_again(self):
        comms_map_filter_set(self.ship, [self.a])
        comms_map_filter_clear(self.ship)
        comms_map_filter_set(self.ship, [self.a])
        self.assertEqual([self.a], self.written())


class TestExtraScanSources(Base):

    def test_A_SHRINKING_LIST_LEAVES_NO_STALE_ENTRIES(self):
        for other in (self.a, self.b, self.c):
            link(self.ship, "extra_scan_source", other)
        extra_scan_sources_run_all(None)
        self.assertEqual(3, len(self.written("extra_scan_source")))
        unlink(self.ship, "extra_scan_source", self.b)
        unlink(self.ship, "extra_scan_source", self.c)
        extra_scan_sources_run_all(None)
        self.assertEqual([self.a], self.written("extra_scan_source"))
        self.assertEqual(1, self.ds.get("num_extra_scan_sources", 0))


class TestMockClearData(Base):

    def test_clear_data_is_a_change(self):
        self.ds.set("comms_map_filter", self.a, 0)
        gen = self.ds.gen
        self.ds.clear_data("comms_map_filter")
        self.assertGreater(self.ds.gen, gen)
        self.assertIn(("comms_map_filter", 0), self.ds.dirty_since(gen))

    def test_clearing_nothing_is_not_a_change(self):
        gen = self.ds.gen
        self.ds.clear_data("never_set")
        self.assertEqual(gen, self.ds.gen)


if __name__ == "__main__":
    unittest.main()
