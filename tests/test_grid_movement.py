"""Grid objects walk their interior, the way the engine walks them.

The numbers here are not invented: they were measured against the real engine on
2026-09-03 by driving an LM damage-control team across a `tsn_battle_cruiser` and
sampling its blob on the engine's own tick. `test_engine_measured_route` replays
that exact traverse.

Before `_physics_grid_movers` existed the mock moved no grid object at all, so
`curx`/`cury` never changed, `grid_arrive_location` never fired, and no headless run
could drive a repair to completion.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from cosmos_dev.mock import sbs  # noqa: E402


class FakeMap:
    """A hull map with a rectangle of open cells and optional walls."""

    def __init__(self, w, h, walls=()):
        self.w = w
        self.h = h
        self.grid_items = []
        self._walls = set(walls)

    def is_grid_point_open(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        return (x, y) not in self._walls


class GridStepTest(unittest.TestCase):
    """The step rule on its own - no sim, no ticking."""

    def test_larger_delta_first(self):
        hm = FakeMap(10, 17)
        # dy dominates -> move in y.
        self.assertEqual(sbs._grid_next_cell(hm, 4, 3, 8, 14), (4, 4))
        # dx dominates -> move in x.
        self.assertEqual(sbs._grid_next_cell(hm, 1, 1, 9, 2), (2, 1))

    def test_tie_goes_to_x(self):
        hm = FakeMap(10, 17)
        self.assertEqual(sbs._grid_next_cell(hm, 4, 10, 8, 14), (5, 10))

    def test_already_there_is_none(self):
        self.assertIsNone(sbs._grid_next_cell(FakeMap(10, 10), 3, 3, 3, 3))

    def test_blocked_greedy_step_falls_back_to_a_real_path(self):
        hm = FakeMap(10, 10, walls={(5, 4)})
        # Greedy would go x (tie), but that cell is a wall.
        step = sbs._grid_next_cell(hm, 4, 4, 8, 8)
        self.assertNotEqual(step, (5, 4), "stepped into the wall")
        self.assertTrue(hm.is_grid_point_open(*step))
        # Still a four-connected move that gets closer.
        self.assertEqual(abs(step[0] - 4) + abs(step[1] - 4), 1)
        self.assertLess(abs(step[0] - 8) + abs(step[1] - 8), 8)

    def test_routes_around_a_bulkhead(self):
        # A wall across the middle with one gap: greedy alone would stall.
        walls = {(x, 5) for x in range(10) if x != 9}
        hm = FakeMap(10, 10, walls=walls)
        cx, cy = 0, 0
        seen = [(cx, cy)]
        for _ in range(80):
            step = sbs._grid_next_cell(hm, cx, cy, 0, 9)
            if step is None:
                break
            cx, cy = step
            seen.append(step)
            if (cx, cy) == (0, 9):
                break
        self.assertEqual(seen[-1], (0, 9), "never got through the gap: %r" % (seen,))
        self.assertNotIn((0, 5), seen, "walked through the bulkhead")

    def test_no_route_at_all_is_none(self):
        """Sealed off: once the greedy step is the wall itself, there is no answer."""
        walls = {(x, 5) for x in range(10)}
        hm = FakeMap(10, 10, walls=walls)
        # From (0,4) the only way on is (0,5), which is the bulkhead.
        self.assertIsNone(sbs._grid_next_cell(hm, 0, 4, 0, 9))


class GridMoverTest(unittest.TestCase):
    """The per-tick mover, driven against a hull map registered with the mock."""

    def setUp(self):
        sbs.create_new_sim()
        self.hm = FakeMap(10, 17)
        self.ship_id = 4242
        sbs.hull_map_objects[self.ship_id] = self.hm

    def tearDown(self):
        sbs.hull_map_objects.pop(self.ship_id, None)

    def _team(self, x, y):
        go = sbs.grid_object()
        b = go.data_set
        for k, v in (("curx", x), ("cury", y), ("lastx", x), ("lasty", y),
                     ("percent", 1.0), ("move_speed", 0), ("pathx", -1), ("pathy", -1)):
            b.set(k, v, 0)
        self.hm.grid_items.append(go)
        return go

    @staticmethod
    def _order(go, x, y, speed):
        b = go.data_set
        b.set("pathx", x, 0)
        b.set("pathy", y, 0)
        b.set("move_speed", speed, 0)

    @staticmethod
    def _cell(go):
        b = go.data_set
        return (int(b.get("curx", 0)), int(b.get("cury", 0)))

    def _run(self, ticks, dt=1.0 / sbs.TICKS_PER_SECOND):
        for _ in range(ticks):
            sbs._physics_grid_movers(dt)

    def test_a_team_with_no_order_does_not_move(self):
        go = self._team(4, 3)
        self._run(200)
        self.assertEqual(self._cell(go), (4, 3))

    def test_path_command_is_consumed_to_minus_one(self):
        go = self._team(4, 3)
        self._order(go, 8, 14, 0.05)
        self._run(1)
        b = go.data_set
        self.assertEqual((b.get("pathx", 0), b.get("pathy", 0)), (-1, -1))

    def test_engine_measured_route(self):
        """The exact cell sequence the engine produced for (4,3) -> (8,14)."""
        expected = [(4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10),
                    (5, 10), (5, 11), (6, 11), (6, 12), (7, 12), (7, 13), (8, 13), (8, 14)]
        go = self._team(4, 3)
        self._order(go, 8, 14, 0.05)
        seen = [self._cell(go)]
        for _ in range(3000):
            self._run(1)
            cell = self._cell(go)
            if cell != seen[-1]:
                seen.append(cell)
            if cell == (8, 14):
                break
        self.assertEqual(seen, expected)

    def test_speed_matches_the_engine_rate(self):
        """move_speed x TICKS_PER_SECOND cells a second - ~1.4 at 0.05, as measured."""
        go = self._team(0, 0)
        self._order(go, 9, 0, 0.05)
        self._run(int(sbs.TICKS_PER_SECOND))          # one sim-second
        travelled = self._cell(go)[0]
        self.assertEqual(travelled, 1, "expected ~1.5 cells in a second, got %d" % travelled)

    def test_arrival_stops_the_team(self):
        go = self._team(4, 3)
        self._order(go, 4, 6, 0.5)
        self._run(400)
        b = go.data_set
        self.assertEqual(self._cell(go), (4, 6))
        self.assertEqual(b.get("move_speed", 0), 0)
        self.assertEqual(b.get("percent", 0), 1.0)
        self.assertIsNone(go._dest)

    def test_last_tracks_cur(self):
        """lastx/lasty are NOT a from/to pair - the engine keeps them equal to cur."""
        go = self._team(4, 3)
        self._order(go, 4, 10, 0.2)
        for _ in range(600):
            self._run(1)
            b = go.data_set
            self.assertEqual((b.get("lastx", 0), b.get("lasty", 0)), self._cell(go))
            if self._cell(go) == (4, 10):
                break
        self.assertEqual(self._cell(go), (4, 10))

    def test_two_teams_move_independently(self):
        a = self._team(0, 0)
        c = self._team(9, 16)
        self._order(a, 0, 8, 0.2)
        self._order(c, 9, 8, 0.2)
        self._run(1500)
        self.assertEqual(self._cell(a), (0, 8))
        self.assertEqual(self._cell(c), (9, 8))

    def test_a_sealed_target_is_refused_not_walked_at(self):
        """No route at all: the team never sets off, and never oscillates.

        The distance field knows on the first step that the target is unreachable, so
        the order is dropped where it stands rather than walking up to the bulkhead to
        find out. What the ENGINE does with an impossible order is not measured - this
        pins the mock to terminating instead of grinding, which is the property the
        soak needs.
        """
        self.hm._walls = {(x, 5) for x in range(self.hm.w)}
        go = self._team(4, 0)
        self._order(go, 4, 9, 0.5)
        self._run(600)
        b = go.data_set
        self.assertEqual(self._cell(go), (4, 0))
        self.assertEqual(b.get("move_speed", 0), 0)
        self.assertIsNone(go._dest)

    def test_a_reachable_target_behind_a_bulkhead_is_reached(self):
        """The same wall with one gap: the team goes the long way round."""
        self.hm._walls = {(x, 5) for x in range(self.hm.w) if x != 9}
        go = self._team(4, 0)
        self._order(go, 4, 9, 0.5)
        self._run(4000)
        self.assertEqual(self._cell(go), (4, 9))


class PathLengthTest(GridMoverTest):
    """`path_length` - cells REMAINING, and the arrival signal the brains turn on.

    Measured against the engine on 2026-09-03: across a real damcon traverse it read 14
    at the moment the order landed and counted down by exactly 1 per cell, reaching 0 on
    arrival.

    This is not cosmetic. `ai_lifeform_move_to_location` treats `path_length < 0.01` as
    HAVING ARRIVED, so while the mock left it unset the blob's typed default of 0 said
    every team was already there - and the whole arrival/idle_state machine collapsed
    with nothing failing anywhere.
    """

    def test_it_is_the_full_distance_when_the_order_lands(self):
        go = self._team(7, 6)
        self._order(go, 1, 14, 0.05)
        self._run(1)
        # Manhattan on an open map: |7-1| + |6-14|.
        self.assertEqual(go.data_set.get("path_length", 0), 14)

    def test_it_loses_exactly_one_per_cell(self):
        go = self._team(7, 6)
        self._order(go, 1, 14, 0.05)
        seen = []
        last = None
        for _ in range(4000):
            self._run(1)
            cell = self._cell(go)
            if cell != last:
                seen.append(go.data_set.get("path_length", 0))
                last = cell
            if cell == (1, 14):
                break
        # 14 at the start cell, then one per step down to 0 - the engine's own trace.
        self.assertEqual(seen, list(range(14, -1, -1)),
                         "path_length did not count down one per step: %r" % (seen,))

    def test_it_is_zero_on_arrival(self):
        go = self._team(4, 3)
        self._order(go, 4, 6, 0.5)
        self._run(400)
        self.assertEqual(self._cell(go), (4, 6))
        self.assertEqual(go.data_set.get("path_length", 0), 0)

    def test_it_counts_the_way_ROUND_a_bulkhead(self):
        """A straight-line estimate would say 9 and be wrong by the whole detour."""
        self.hm._walls = {(x, 5) for x in range(self.hm.w) if x != 9}
        go = self._team(4, 0)
        self._order(go, 4, 9, 0.5)
        self._run(1)
        direct = abs(4 - 4) + abs(0 - 9)
        self.assertGreater(go.data_set.get("path_length", 0), direct,
                           "path_length ignored the bulkhead")

    def test_a_sealed_target_leaves_it_at_zero(self):
        self.hm._walls = {(x, 5) for x in range(self.hm.w)}
        go = self._team(4, 0)
        self._order(go, 4, 9, 0.5)
        self._run(50)
        self.assertEqual(go.data_set.get("path_length", 0), 0)


class GridMoverWiringTest(unittest.TestCase):
    """The mover is actually CALLED by the sim's physics tick.

    The tests above drive `_physics_grid_movers` directly, so they pin the routing rule
    but say nothing about whether anything ever runs it - disable the call in
    `_physics_tick_locked` and every one of them still passes. This is the test that
    fails when the wiring is missing, which is the state the mock was in.
    """

    def setUp(self):
        sbs.create_new_sim()
        self.hm = FakeMap(10, 17)
        self.ship_id = 5150
        sbs.hull_map_objects[self.ship_id] = self.hm

    def tearDown(self):
        sbs.hull_map_objects.pop(self.ship_id, None)

    def test_a_team_walks_when_the_sim_ticks(self):
        go = sbs.grid_object()
        b = go.data_set
        for k, v in (("curx", 4), ("cury", 3), ("lastx", 4), ("lasty", 3),
                     ("percent", 1.0), ("move_speed", 0), ("pathx", -1), ("pathy", -1)):
            b.set(k, v, 0)
        self.hm.grid_items.append(go)
        b.set("pathx", 4, 0)
        b.set("pathy", 9, 0)
        b.set("move_speed", 0.2, 0)

        sbs.sim._paused = False
        for _ in range(600):
            sbs.physics_tick(1.0 / sbs.TICKS_PER_SECOND)
            if (b.get("curx", 0), b.get("cury", 0)) == (4, 9):
                break
        self.assertEqual((b.get("curx", 0), b.get("cury", 0)), (4, 9),
                         "the physics tick never moved the team")


if __name__ == "__main__":
    unittest.main()
