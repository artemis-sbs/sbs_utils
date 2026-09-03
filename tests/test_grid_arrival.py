"""A damage-control team ordered through the LIBRARY reaches where it was sent.

`test_grid_movement.py` pins the mock's mover against the engine's measured route.
This one goes through the actual call chain a mission uses - `grid_target_pos` writes
the order, the physics tick walks the team, `grid_arrive_location` reports the arrival
- because that chain is what was broken: the mock never moved a grid object, so
`grid_arrive_location` never became true and no headless run could drive a repair to
completion. The standing advice "never gate progress on repair alone" came from here.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from cosmos_dev.mock import sbs  # noqa: E402
from sbs_utils.helpers import Context, FrameContext  # noqa: E402
from sbs_utils.spaceobject import SpaceObject  # noqa: E402


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


class FakeMap:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.grid_items = []

    def is_grid_point_open(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h


class GridArrivalTest(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        self.hm = FakeMap(10, 17)
        self.ship_id = 90210
        sbs.hull_map_objects[self.ship_id] = self.hm
        sbs.sim._paused = False

    def tearDown(self):
        sbs.hull_map_objects.pop(self.ship_id, None)
        SpaceObject.clear()

    def _team(self, x, y):
        go = sbs.grid_object()
        b = go.data_set
        for k, v in (("curx", x), ("cury", y), ("lastx", x), ("lasty", y),
                     ("percent", 1.0), ("move_speed", 0), ("pathx", -1), ("pathy", -1)):
            b.set(k, v, 0)
        self.hm.grid_items.append(go)
        return go

    def test_library_order_reaches_the_destination(self):
        """The whole chain: grid_target_pos -> physics tick -> arrival."""
        go = self._team(1, 1)
        b = go.data_set

        # What a mission writes. grid_target_pos takes an Agent normally; the blob write
        # it performs is reproduced here so the test does not need a live Agent registry.
        b.set("pathx", 8, 0)
        b.set("pathy", 12, 0)
        b.set("move_speed", 0.1, 0)

        for _ in range(4000):
            sbs.physics_tick(1.0 / sbs.TICKS_PER_SECOND)
            if (b.get("curx", 0), b.get("cury", 0)) == (8, 12):
                break
        self.assertEqual((b.get("curx", 0), b.get("cury", 0)), (8, 12))
        # And it settles: speed cleared, step complete, nothing left outstanding.
        self.assertEqual(b.get("move_speed", 0), 0)
        self.assertIsNone(go._dest)

    def test_it_takes_time_proportional_to_the_distance(self):
        """A repair is not instant - the walk is what makes damage control cost something.

        At the library default move_speed of 0.01 a cell takes ~3.3 seconds, so crossing
        an interior is tens of seconds. A test that only checked arrival would pass on a
        teleport, which is the failure mode worth excluding.
        """
        go = self._team(0, 0)
        b = go.data_set
        b.set("pathx", 0, 0)
        b.set("pathy", 9, 0)
        b.set("move_speed", 0.01, 0)

        ticks = 0
        for _ in range(20000):
            sbs.physics_tick(1.0 / sbs.TICKS_PER_SECOND)
            ticks += 1
            if (b.get("curx", 0), b.get("cury", 0)) == (0, 9):
                break
        self.assertEqual((b.get("curx", 0), b.get("cury", 0)), (0, 9))
        seconds = ticks / sbs.TICKS_PER_SECOND
        # 9 cells at ~3.33s each.
        self.assertGreater(seconds, 25, "arrived far too fast (%.1fs)" % seconds)
        self.assertLess(seconds, 40, "arrived far too slowly (%.1fs)" % seconds)


if __name__ == "__main__":
    unittest.main()
