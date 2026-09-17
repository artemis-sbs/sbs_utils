"""The LANE: a corridor wide enough to actually fly down.

Measured over all seven Storm's Beacon relics and all 254 pairs of places, every route's
tightest point was EXACTLY `RAIL_MARGIN` - 20 units. Not a near miss: every legal leg cost
exactly its length, so a shortest-path search always took the inside of the corner, and
the margin is where the inside of the corner is.

Meanwhile the flight helped itself to far more: a rope of 140, a drift of 90, and a
waypoint counted as reached 120 units early. The corridor anyone had proved was a seventh
of the thing flying down it, and the overflow went into the rock.

So a leg now costs its length TIMES how tight it is. The load-bearing distinction, and
what most of this file is about: that is a COST and never a refusal. A relic whose only
way in is a 50-unit slab must still fly.

    python -m unittest tests.test_rail_lane
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  breaks a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural import rails as R
from sbs_utils.procedural.rails import (RAIL_LANE, RAIL_MARGIN, rail_build, rail_get,
                                        rail_lane, rail_leg_clearance, rail_remove,
                                        rail_route)
from sbs_utils.procedural.volume import _vol_resolve, volume_define, volume_remove


def _clear(vol, p):
    return -vol.depth(p)


class TightnessTests(unittest.TestCase):
    def test_a_comfortable_leg_is_not_penalised(self):
        self.assertEqual(R._rail_tightness(RAIL_LANE, RAIL_LANE), 1.0)
        self.assertEqual(R._rail_tightness(RAIL_LANE * 3, RAIL_LANE), 1.0)

    def test_a_leg_with_no_room_costs_the_most(self):
        self.assertEqual(R._rail_tightness(0.0, RAIL_LANE), R.RAIL_TIGHT_PENALTY)

    def test_it_rises_as_the_room_runs_out(self):
        wide = R._rail_tightness(RAIL_LANE * 0.9, RAIL_LANE)
        narrow = R._rail_tightness(RAIL_LANE * 0.2, RAIL_LANE)
        self.assertLess(wide, narrow)
        self.assertGreater(wide, 1.0)

    def test_it_is_never_infinite(self):
        """A penalty is not a refusal. Anything unbounded here would silently disconnect
        a relic whose only way through is tight."""
        for c in (-500.0, 0.0, 1.0, 20.0):
            self.assertLessEqual(R._rail_tightness(c, RAIL_LANE), R.RAIL_TIGHT_PENALTY)


class _VolTest(unittest.TestCase):
    NAME = "__lane_test__"

    def tearDown(self):
        rail_remove(self.NAME)
        volume_remove(self.NAME)

    def _build(self, boxes, places, **kw):
        reset_mock(sbs)
        rail_remove(self.NAME)
        volume_remove(self.NAME)
        volume_define(self.NAME, boxes=boxes)
        return rail_build(self.NAME, places=places, **kw)


class CenteringTests(_VolTest):
    def test_nodes_come_off_the_wall(self):
        """A place authored hard against a bulkhead is a label on a room, not a station.
        Every node in all seven shipped relics sat at exactly 20.0 before this."""
        st = self._build({"hall": (0, 0, 0, 1500, 600, 600)},
                         {"wallside": (0, 590, 0)})
        vol = _vol_resolve(self.NAME)
        web = rail_get(self.NAME)
        self.assertGreater(_clear(vol, web.nodes["wallside"]["pos"]), RAIL_MARGIN * 2)
        self.assertGreater(st["node_min"], RAIL_MARGIN)

    def test_centering_stops_at_the_lane(self):
        """Pushing every node to the centroid would collapse a wide room back to the one
        crossing the web exists to avoid."""
        big = 4000.0
        self._build({"hall": (0, 0, 0, big, big, big)}, {"a": (-3000, 0, 0)})
        vol = _vol_resolve(self.NAME)
        web = rail_get(self.NAME)
        pos = web.nodes["a"]["pos"]
        self.assertLess(abs(pos[0]), big)
        self.assertGreater(_clear(vol, pos), RAIL_MARGIN)
        self.assertGreater(abs(pos[0]), 500.0)

    def test_a_node_is_never_left_outside(self):
        st = self._build({"hall": (0, 0, 0, 800, 400, 400)}, {"far": (5000, 0, 0)})
        vol = _vol_resolve(self.NAME)
        web = rail_get(self.NAME)
        self.assertGreater(_clear(vol, web.nodes["far"]["pos"]), 0.0)
        self.assertGreaterEqual(st["node_min"], 0.0)


class ConnectivityTests(_VolTest):
    # BOXES MUST OVERLAP, NOT ABUT. A zero-thickness join reads as one connected space
    # (a point on the shared plane is inside both) while nothing can actually be placed
    # in it - the `sink` bug. Each pair here shares 200 units of real volume.
    TIGHT = {"west": (-1250, 0, 0, 1250, 500, 500),     # x -2500..0
             "throat": (0, 0, 0, 200, 35, 35),          # x  -200..200, only 70 tall
             "east": (1250, 0, 0, 1250, 500, 500)}      # x     0..2500
    ENDS = {"a": (-2000, 0, 0), "b": (2000, 0, 0)}

    def test_a_relic_whose_only_way_is_tight_still_routes(self):
        """THE ANTI-REGRESSION. `false_choir`'s throat meets its concourse in a 50-unit
        slab. Turn the tightness cost into a requirement and that relic stops flying."""
        st = self._build(self.TIGHT, self.ENDS)
        self.assertEqual(st["components"], 1, "a tight way is still a way")
        web = rail_get(self.NAME)
        self.assertTrue(rail_route(self.NAME, web.nodes["a"]["pos"], "b"))

    def test_the_tight_legs_are_reported_not_hidden(self):
        st = self._build(self.TIGHT, self.ENDS)
        self.assertGreater(st["tight"], 0)
        self.assertLess(st["lane_min"], RAIL_LANE)
        self.assertEqual(st["lane"], RAIL_LANE)


class PrefersTheOpenWayTests(_VolTest):
    """A short scrape past a corner against a longer open way round.

    Tested as an A/B against the mechanism being OFF (`lane=0` makes every leg
    comfortable, so cost collapses back to pure length - exactly the old behaviour).
    That pins what actually changed rather than a hand-tuned geometry: how far a route
    is willing to go round is a judgement call in `RAIL_TIGHT_PENALTY`, but that it goes
    round FURTHER than it used to is the whole feature.
    """

    #: A narrow shaft straight up the middle, and a wide way round the outside.
    SHAFT = {"start": (0, 0, 0, 600, 400, 400),
             "tight": (0, 0, 1100, 45, 45, 1200),        # z -100..2300, 90 wide
             "open_a": (900, 0, 0, 500, 400, 400),
             "riser": (1300, 0, 1100, 400, 400, 1300),   # z -200..2400, 800 wide
             "open_b": (900, 0, 2200, 500, 400, 400),
             "end": (0, 0, 2200, 600, 400, 400)}
    ENDS = {"a": (0, 0, -400), "b": (0, 0, 2500)}

    def _route_clearance(self, **kw):
        self._build(self.SHAFT, self.ENDS, **kw)
        web = rail_get(self.NAME)
        chain = rail_route(self.NAME, web.nodes["a"]["pos"], "b")
        self.assertTrue(chain)
        vol = _vol_resolve(self.NAME)
        return min(_clear(vol, p) for p in chain), chain

    def test_the_penalty_buys_real_clearance(self):
        """THE A/B. Same geometry, same web, one number different."""
        flat, _ = self._route_clearance(lane=0.0)         # cost == length, as before
        laned, _ = self._route_clearance()                 # cost == length * tightness
        self.assertGreater(
            laned, flat,
            "the tightness cost bought no clearance - a route with it on should keep "
            "further from the rock than one with it off")

    def test_both_still_arrive(self):
        """Whatever it costs, it is never a refusal."""
        for kw in ({"lane": 0.0}, {}):
            _c, chain = self._route_clearance(**kw)
            self.assertTrue(chain)


class LegClearanceTests(_VolTest):
    HALL = {"hall": (0, 0, 0, 1500, 400, 400)}
    ENDS = {"a": (-1200, 0, 0), "b": (1200, 0, 0)}

    def test_it_is_not_wildly_optimistic(self):
        """The cache samples coarsely, so it may read slightly high - but never by enough
        to call a scrape a comfortable run."""
        self._build(self.HALL, self.ENDS)
        web = rail_get(self.NAME)
        vol = _vol_resolve(self.NAME)
        for (a, b), cached in list(web.clear.items())[:12]:
            pa, pb = web.nodes[a]["pos"], web.nodes[b]["pos"]
            sampled = min(_clear(vol, (pa[0] + (pb[0] - pa[0]) * i / 32.0,
                                       pa[1] + (pb[1] - pa[1]) * i / 32.0,
                                       pa[2] + (pb[2] - pa[2]) * i / 32.0))
                          for i in range(33))
            self.assertLess(cached - sampled, 60.0)

    def test_the_accessors_answer(self):
        self._build(self.HALL, self.ENDS)
        self.assertEqual(rail_lane(self.NAME), RAIL_LANE)
        web = rail_get(self.NAME)
        a = next(iter(web.edges))
        b = next(iter(web.edges[a]))
        self.assertIsNotNone(rail_leg_clearance(self.NAME, a, b))

    def test_unknown_names_are_none_not_an_error(self):
        self.assertIsNone(rail_lane("nope"))
        self.assertIsNone(rail_leg_clearance("nope", "a", "b"))


class RecoveryTests(_VolTest):
    SPLIT = {"hall": (0, 0, 0, 1200, 400, 400),
             "side": (1600, 0, 0, 600, 400, 400)}
    ENDS = {"a": (-1000, 0, 0), "b": (2000, 0, 0)}

    def test_a_route_out_of_solid_rock(self):
        """WHAT REPLACES CONTAINMENT. Visibility is measured from where the ship is, and
        from inside the plating nothing is visible - so a stuck suit attached to nothing
        and was told 'no way through'. Only the tractor rescued it, and the tractor no
        longer watches suits."""
        self._build(self.SPLIT, self.ENDS)
        vol = _vol_resolve(self.NAME)
        buried = (0.0, 900.0, 0.0)
        self.assertLess(_clear(vol, buried), 0.0, "the fixture must start in the rock")
        chain = rail_route(self.NAME, buried, "b")
        self.assertTrue(chain, "a suit in a wall would be stuck for good")
        self.assertGreater(_clear(vol, chain[0]), 0.0,
                           "the first leg must head OUT of the rock")

    def test_an_ordinary_route_is_unaffected(self):
        self._build(self.SPLIT, self.ENDS)
        web = rail_get(self.NAME)
        self.assertTrue(rail_route(self.NAME, web.nodes["a"]["pos"], "b"))


if __name__ == "__main__":
    unittest.main()
