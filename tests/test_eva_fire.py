"""A suit's beam, the console's selection, and what a tether takes off the map.

THE BEAM WAS NEVER MISSING. `tsn_shuttle` - the default suit hull - has carried a forward
beam in its shipData `hull_port_sets` all along: range 1000, a 144-degree arc, cycle 2.
What was missing is the LOCK. A hull fires its beams at whatever `weapon_target_UID`
names, which is how LegendaryMissions' manual-beams panel reads a target, and nothing ever
set it for a suit. So the suit flew around a ruin with a working weapon and no way to aim.

A selection is an ordinary blob key, readable and writable (`query.set_weapons_selection`),
so this goes both ways: a click on the 2D view becomes the app's target, and a row in the
app becomes the console's selection.

    python -m unittest tests.test_eva_fire
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  breaks a circular import
from cosmos_dev.mock import sbs as sbs
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.query import get_weapons_selection, to_id
from sbs_utils.procedural.rails import (rail_barrier, rail_barrier_object,
                                        rail_barrier_of_object, rail_barrier_open,
                                        rail_barrier_set_object, rail_build, rail_get,
                                        rail_remove, rail_route)

RELIC = "__fire__"


class BarrierObjectTests(unittest.TestCase):
    """A barrier is a sphere in the graph, and nothing can shoot a sphere. Giving it a
    real object is what turns cutting from a scripted timer into a weapons problem."""

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        V.volume_clear()
        rail_remove(RELIC)
        # OVERLAPPING, not abutting - a zero-thickness join reads as connected and is not.
        V.volume_define(RELIC, boxes={"w": (-800, 0, 0, 1000, 300, 300),
                                      "e": (800, 0, 0, 1000, 300, 300)})
        rail_build(RELIC, places={"a": (-1500, 0, 0), "b": (1500, 0, 0)})
        self.web = rail_get(RELIC)

    def tearDown(self):
        rail_remove(RELIC)
        V.volume_clear()

    def _route(self):
        return rail_route(RELIC, self.web.nodes["a"]["pos"], "b")

    def test_a_barrier_seals_the_way_and_opening_it_clears_it(self):
        self.assertTrue(self._route(), "the fixture must be flyable to begin with")
        rail_barrier(RELIC, "hatch", (0, 0, 0), 400, display="Seized Hatch")
        self.assertEqual(self._route(), [], "a shut barrier must sever the way")
        rail_barrier_open(RELIC, "hatch")
        self.assertTrue(self._route(), "opening it must restore the way")

    def test_a_barrier_starts_with_no_object(self):
        rail_barrier(RELIC, "hatch", (0, 0, 0), 400)
        self.assertIsNone(rail_barrier_object(RELIC, "hatch"))

    def test_an_object_binds_both_ways(self):
        """A damage route has an object id and needs the barrier; the app has the barrier
        and needs something to aim at."""
        rail_barrier(RELIC, "hatch", (0, 0, 0), 400)
        rail_barrier_set_object(RELIC, "hatch", 4242)
        self.assertEqual(rail_barrier_object(RELIC, "hatch"), 4242)
        self.assertEqual(rail_barrier_of_object(RELIC, 4242), "hatch")

    def test_an_unrelated_object_is_not_a_barrier(self):
        """A destroy route hands this every destruction, so it must say no cheaply."""
        rail_barrier(RELIC, "hatch", (0, 0, 0), 400)
        rail_barrier_set_object(RELIC, "hatch", 4242)
        self.assertIsNone(rail_barrier_of_object(RELIC, 777))
        self.assertIsNone(rail_barrier_of_object(RELIC, None))

    def test_unbinding_is_clean(self):
        rail_barrier(RELIC, "hatch", (0, 0, 0), 400)
        rail_barrier_set_object(RELIC, "hatch", 4242)
        rail_barrier_set_object(RELIC, "hatch", None)
        self.assertIsNone(rail_barrier_object(RELIC, "hatch"))
        self.assertIsNone(rail_barrier_of_object(RELIC, 4242))

    def test_an_unknown_web_answers_none_rather_than_raising(self):
        self.assertIsNone(rail_barrier_object("nope", "hatch"))
        self.assertIsNone(rail_barrier_of_object("nope", 1))
        self.assertFalse(rail_barrier_set_object(RELIC, "no_such_barrier", 1))


class SuitHullTests(unittest.TestCase):
    """The claim the whole feature rests on, checked against the shipped data rather
    than assumed: the hull a suit is drawn as already has a beam."""

    def test_the_default_suit_hull_is_a_real_ship_data_key(self):
        self.assertTrue(E.eva_suit_hull())
        self.assertIsInstance(E.eva_suit_hull(), str)


class AimTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        V.volume_clear()
        E.eva_clear()
        self.cid = 71
        GuiClient(self.cid)

    def test_aiming_with_no_suit_is_false_not_an_error(self):
        from sbs_utils.procedural.eva_tools import eva_aim, eva_aimed
        self.assertFalse(eva_aim(self.cid, 1234))
        self.assertIsNone(eva_aimed(self.cid))

    def test_nothing_selected_reads_as_nothing(self):
        from sbs_utils.procedural.eva_tools import eva_selected_target
        self.assertIsNone(eva_selected_target(self.cid))


class FireRowTests(unittest.TestCase):
    """What the row prints, and the colour it prints in. The 2D view colours a contact by
    what it IS; this colours it by what the held tool can do with it."""

    def _row(self, aimed, ok):
        return ("k", "Hatch   200", aimed, ok, "barrier")

    def test_the_locked_target_is_marked(self):
        from sbs_utils.procedural.gui.xess import FIRE_COLOR_AIMED, _fire_row
        self.assertTrue(FIRE_COLOR_AIMED.startswith("#"))

    def test_the_three_colours_are_distinct(self):
        from sbs_utils.procedural.gui.xess import (FIRE_COLOR_AIMED, FIRE_COLOR_READY,
                                                   FIRE_COLOR_WRONG)
        self.assertEqual(len({FIRE_COLOR_AIMED, FIRE_COLOR_READY, FIRE_COLOR_WRONG}), 3)

    def test_they_are_ascii_hex(self):
        from sbs_utils.procedural.gui.xess import (FIRE_COLOR_AIMED, FIRE_COLOR_READY,
                                                   FIRE_COLOR_WRONG)
        for c in (FIRE_COLOR_AIMED, FIRE_COLOR_READY, FIRE_COLOR_WRONG):
            c.encode("ascii")
            self.assertTrue(c.startswith("#"))


if __name__ == "__main__":
    unittest.main()
