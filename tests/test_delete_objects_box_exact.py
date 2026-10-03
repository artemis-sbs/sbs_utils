"""`delete_objects_box` deletes what is IN the box, not whatever the broad test hands back.

Measured in the engine, 2026-10-03, on an Open Universe jump. The jump builds the
destination system 250,000 units away and then clears the system it left with a box
around the origin, half-extent 100,000:

    broad_test returned= 1006 | really inside= 1002 | OUTSIDE the box= 4
    examples outside= [('Raw Ore', -261814, -239384), ('Derelict', -237498, -254939), ...]

The four were everything the destination had - spawned a moment earlier, and handed back
by the engine's broad test for a box they were nowhere near. `delete_objects_box` checked
height and nothing else, so it deleted them: the crew arrived at Ferrow Landing and there
was no Ferrow Landing. The mock's broad test is exact, so nothing headless ever saw it.

A broad test is a coarse first pass. The sphere version has always re-checked distance;
the box version now re-checks the box.

    python -m unittest tests.test_delete_objects_box_exact
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.space_objects import delete_objects_box


class TheBoxIsExactTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        DeleteQueue.clear()
        self.addCleanup(DeleteQueue.clear)
        # npc_spawn, not the a2x enemy helper: that one converts Artemis 2 coordinates, so
        # "1000, 0, -2000" lands at (99000, 0, 102000) and the fixture means nothing.
        self.near = self.put(1000, 0, -2000, "Near")
        self.far_x = self.put(-250000, 0, 0, "FarX")
        self.far_z = self.put(0, 0, -250000, "FarZ")
        self.high = self.put(0, 150000, 0, "High")
        for obj_id, want in ((self.near, (1000, 0, -2000)), (self.far_x, (-250000, 0, 0))):
            pos = to_object(obj_id).pos
            self.assertEqual((pos.x, pos.y, pos.z), want)
        # THE ENGINE'S ANSWER, as measured: everything, including what is nowhere near.
        self._real = sbs.broad_test
        everything = [to_object(i).engine_object
                      for i in (self.near, self.far_x, self.far_z, self.high)]
        sbs.broad_test = lambda x1, z1, x2, z2, broad_type: list(everything)
        self.addCleanup(setattr, sbs, "broad_test", self._real)

    def put(self, x, y, z, name):
        return to_id(npc_spawn(x, y, z, name, "raider", "kralien_cruiser", "behav_npcship"))

    def alive(self, obj_id):
        return to_object(obj_id) is not None

    def test_what_is_inside_is_deleted(self):
        delete_objects_box(0, 0, 0, 100000, 100000, 100000, broad_type=0x1F)
        self.assertFalse(self.alive(self.near))

    def test_what_is_outside_on_x_survives_even_when_the_broad_test_returns_it(self):
        delete_objects_box(0, 0, 0, 100000, 100000, 100000, broad_type=0x1F)
        self.assertTrue(self.alive(self.far_x))

    def test_what_is_outside_on_z_survives(self):
        delete_objects_box(0, 0, 0, 100000, 100000, 100000, broad_type=0x1F)
        self.assertTrue(self.alive(self.far_z))

    def test_the_height_check_still_holds(self):
        delete_objects_box(0, 0, 0, 100000, 100000, 100000, broad_type=0x1F)
        self.assertTrue(self.alive(self.high))

    def test_the_edge_is_inside(self):
        edge = self.put(100000, 0, -100000, "Edge")
        sbs.broad_test = lambda x1, z1, x2, z2, broad_type: [to_object(edge).engine_object]
        delete_objects_box(0, 0, 0, 100000, 100000, 100000, broad_type=0x1F)
        self.assertFalse(self.alive(edge))


if __name__ == "__main__":
    unittest.main()
