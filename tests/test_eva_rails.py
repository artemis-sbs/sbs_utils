"""EVA on the rail web: drift, the rope, barriers and what the Nav list offers.

`test_eva.py` covers the body model - six consoles, six suits, nothing keyed by the relic.
This covers what changed when the route stopped being re-derived per trip: the web is
solved once, a party spreads out on it rather than flying single file, a shut way is
genuinely shut, and things placed in the ruin are somewhere you can be SENT.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.spaceobject import SpaceObject

CONSOLES = [61, 62, 63, 64]
RELIC = "rail_relic"


def _dist(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


class _Base(unittest.TestCase):
    """A hall, a side chamber and a way round - enough to have a second route."""

    #: Two ways from the west end to the east end: the straight hall, and a loop south.
    #: The loop is what makes a barrier test mean anything - shutting the hall has to
    #: change the route rather than end it.
    BOXES = {
        "hall": (0, 0, 0, 2400, 200, 200),
        "wleg": (-2400, 0, 900, 200, 200, 900),
        "eleg": (2400, 0, 900, 200, 200, 900),
        "loop": (0, 0, 1700, 2400, 200, 200),
    }
    POINTS = {
        "west end": [-2300, 0, 0, ["entrance"], "The West End"],
        "east end": [2300, 0, 0, ["room"], "The East End"],
    }

    def setUp(self):
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        R._RELIC_RECORDS.clear()
        R._ARMED.clear()
        for cid in CONSOLES:
            GuiClient(cid)
        V.volume_define(RELIC, boxes=dict(self.BOXES))
        R._RELIC_RECORDS[RELIC] = {
            "key": RELIC, "loc": (0, 0, 0), "volume": RELIC,
            "points": {k: list(v) for k, v in self.POINTS.items()},
            "barriers": {}, "contents": [],
        }
        R.relic_rails_ensure(RELIC)

    def tearDown(self):
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        R._RELIC_RECORDS.clear()
        R._ARMED.clear()

    def suit_up(self, cid, at=(-2300, 0, 0)):
        who = lifeform_spawn("Boarder %d" % cid, "terran_male", "boarding")
        suit = E.eva_suit_spawn(who, RELIC, at[0], at[1], at[2],
                                hull="tsn_shuttle", side="tsn", volume=RELIC)
        E.eva_take(cid, suit, RELIC, volume=RELIC)
        return suit

    def fly(self, seconds, cids=None):
        """Run the real physics and the real tick, recording where each suit went."""
        from sbs_utils.tickdispatcher import TickDispatcher
        cids = cids or []
        track = {cid: [] for cid in cids}
        for _ in range(int(seconds * 30)):
            sbs.physics_tick(1 / 30)
            TickDispatcher.dispatch_tick()
            for cid in cids:
                obj = to_object(E.eva_my_suit(cid))
                if obj is not None:
                    track[cid].append((obj.pos.x, obj.pos.y, obj.pos.z))
        return track


class ThePartyDoesNotFlySingleFile(_Base):
    def test_two_suits_on_one_route_fly_different_lines(self):
        """The whole of the drift: six consoles on the same web to the same place used to
        fly the same line to within a metre, which reads as one suit and five copies."""
        for cid in CONSOLES[:2]:
            self.suit_up(cid)
            self.assertTrue(E.eva_goto(cid, "east end"))
        track = self.fly(30, CONSOLES[:2])
        gaps = [_dist(a, b) for a, b in zip(track[CONSOLES[0]], track[CONSOLES[1]])]
        self.assertGreater(max(gaps), 20.0,
                           "the two suits flew the same line - the drift did nothing")

    def test_the_drift_is_the_same_every_tick_for_one_suit(self):
        """A drift that wandered would read as a suit that cannot hold a course. It is a
        pure function of the suit's id, so there is nothing to wander."""
        suit = self.suit_up(CONSOLES[0])
        here, aim = (0.0, 0.0, 0.0), (1000.0, 0.0, 0.0)
        first = E._eva_drift(suit, here, aim, RELIC, 400.0)
        for _ in range(5):
            self.assertEqual(E._eva_drift(suit, here, aim, RELIC, 400.0), first)

    def test_a_tight_passage_gets_single_file(self):
        """Single file is what single file is FOR. The drift is bounded by the room
        actually available, so a 60-unit passage gets none of it."""
        suit = self.suit_up(CONSOLES[0])
        here, aim = (0.0, 0.0, 0.0), (1000.0, 0.0, 0.0)
        self.assertEqual(E._eva_drift(suit, here, aim, RELIC, 25.0), aim)

    def test_the_drift_never_leaves_the_volume(self):
        """It is decoration. The wall is not."""
        suit = self.suit_up(CONSOLES[0])
        aim = (2300.0, 0.0, 0.0)
        got = E._eva_drift(suit, (0.0, 0.0, 0.0), aim, RELIC, 4000.0)
        self.assertLessEqual(V.volume_depth(RELIC, got), -E.ROUTE_MARGIN + 1e-6)


class TheRopeHoldsTheSuitToItsLeg(_Base):
    def test_a_suit_far_off_its_leg_is_aimed_back_at_it(self):
        leg_start = (-2000.0, 0.0, 0.0)
        aim = (2000.0, 0.0, 0.0)
        wide = (0.0, 0.0, 400.0)         # well off the line between them
        pulled = E._eva_rope(wide, aim, leg_start)
        self.assertNotEqual(tuple(pulled), tuple(aim))
        self.assertLess(abs(pulled[2]), abs(aim[2]) + 400.0)
        self.assertLess(_dist(pulled, (0.0, 0.0, 0.0)), _dist(aim, (0.0, 0.0, 0.0)))

    def test_a_suit_on_its_leg_is_left_alone(self):
        """Inside the rope the autopilot is untouched - the rope is a limit, not a
        steering input."""
        leg_start = (-2000.0, 0.0, 0.0)
        aim = (2000.0, 0.0, 0.0)
        self.assertEqual(E._eva_rope((0.0, 0.0, 10.0), aim, leg_start), aim)

    def test_no_leg_means_no_rope(self):
        aim = (2000.0, 0.0, 0.0)
        self.assertEqual(E._eva_rope((0.0, 0.0, 400.0), aim, None), aim)


class ABarredWayIsBarred(_Base):
    def test_shutting_the_hall_sends_the_suit_round_the_loop(self):
        self.suit_up(CONSOLES[0])
        self.assertTrue(E.eva_goto(CONSOLES[0], "east end"))
        direct = E.eva_route(CONSOLES[0])[1]
        E.eva_stop(CONSOLES[0])
        self.assertTrue(RL.rail_barrier(RELIC, "the fall", (0, 0, 0), 500))
        self.assertTrue(E.eva_goto(CONSOLES[0], "east end"),
                        "one way shut should reroute, not strand")
        route = E.eva_my_suit(CONSOLES[0]) and E.eva_route(CONSOLES[0])
        self.assertGreater(route[1], 1)
        way = R._RELIC_RECORDS[RELIC]
        self.assertTrue(way)  # the record survived the reroute
        self.assertNotEqual(direct, route[1])

    def test_shutting_both_ways_refuses_the_trip(self):
        """A refusal is honest and visible. Flying the straight line instead is flying
        through the rock, which is the one failure this whole mode exists to prevent."""
        self.suit_up(CONSOLES[0])
        RL.rail_barrier(RELIC, "the fall", (0, 0, 0), 500)
        RL.rail_barrier(RELIC, "the flood", (0, 0, 1700), 500)
        self.assertFalse(E.eva_goto(CONSOLES[0], "east end"))
        self.assertEqual(E.eva_no_way(CONSOLES[0]), "east end")
        self.assertEqual(E.eva_route(CONSOLES[0])[0], None)

    def test_opening_it_lets_the_trip_happen(self):
        self.suit_up(CONSOLES[0])
        RL.rail_barrier(RELIC, "the fall", (0, 0, 0), 500)
        RL.rail_barrier(RELIC, "the flood", (0, 0, 1700), 500)
        self.assertFalse(E.eva_goto(CONSOLES[0], "east end"))
        self.assertTrue(R.relic_open_barrier(RELIC, "the fall"))
        self.assertTrue(E.eva_goto(CONSOLES[0], "east end"))
        self.assertIsNone(E.eva_no_way(CONSOLES[0]),
                          "the refusal should be cleared by the trip that succeeded")


class WhatTheNavListOffers(_Base):
    def test_a_late_cache_becomes_somewhere_you_can_be_sent(self):
        """"Access to other things": a cache placed by a trigger joins the web when it
        appears, rather than being something you have to happen to fly past."""
        self.suit_up(CONSOLES[0])
        before = [row[0] for row in E.eva_points(CONSOLES[0])]
        self.assertNotIn("the locker", before)
        self.assertTrue(RL.rail_attach(RELIC, "the locker", (2300, 0, 1700),
                                       roles=("salvage",), display="A Sealed Locker"))
        after = E.eva_points(CONSOLES[0])
        self.assertIn("the locker", [row[0] for row in after])
        self.assertIn("A Sealed Locker", [row[1] for row in after])
        self.assertTrue(E.eva_goto(CONSOLES[0], "the locker"))

    def test_derived_waypoints_are_never_offered(self):
        """A station through a hall is how you get somewhere, not somewhere to go."""
        self.suit_up(CONSOLES[0])
        for name, _display, _pos in E.eva_points(CONSOLES[0]):
            self.assertFalse(name.startswith("@"), "%s is a waypoint, not a place" % name)

    def test_a_hidden_place_is_off_the_list_but_still_on_the_web(self):
        self.suit_up(CONSOLES[0])
        RL.rail_attach(RELIC, "the vault", (2300, 0, 1700), hidden=True,
                       display="The Vault")
        self.assertNotIn("the vault", [r[0] for r in E.eva_points(CONSOLES[0])])
        # Still reachable: stumbling into a secret on the way somewhere else is the point.
        self.assertTrue(E.eva_goto(CONSOLES[0], "the vault"))

    def test_revealing_puts_it_on_the_list(self):
        self.suit_up(CONSOLES[0])
        RL.rail_attach(RELIC, "the vault", (2300, 0, 1700), hidden=True)
        RL.rail_reveal(RELIC, "the vault")
        self.assertIn("the vault", [r[0] for r in E.eva_points(CONSOLES[0])])

    def test_the_list_is_still_nearest_first(self):
        self.suit_up(CONSOLES[0])
        rows = E.eva_points(CONSOLES[0])
        here = (-2300.0, 0.0, 0.0)
        gaps = [_dist(here, row[2]) for row in rows]
        self.assertEqual(gaps, sorted(gaps))


class TheWebIsSolvedOnceNotPerTrip(_Base):
    def test_the_web_survives_repeated_routing(self):
        """The point of the change: a second destination costs a Dijkstra, not a fresh
        solve of the ruin's geometry."""
        self.suit_up(CONSOLES[0])
        stats = RL.rail_stats(RELIC)
        for _ in range(5):
            E.eva_goto(CONSOLES[0], "east end")
            E.eva_stop(CONSOLES[0])
        self.assertEqual(RL.rail_stats(RELIC)["nodes"], stats["nodes"])
        self.assertEqual(RL.rail_stats(RELIC)["build_ms"], stats["build_ms"],
                         "the web was re-solved - that is the cost this removed")

    def test_a_volume_rebuild_does_not_leave_a_stale_web(self):
        """A web is solved FROM a volume, so one that outlives its geometry describes a
        ruin that is not there - and the next route walks it without noticing."""
        self.assertIsNotNone(RL.rail_get(RELIC))
        V.volume_remove(RELIC)
        self.assertIsNone(RL.rail_get(RELIC))


if __name__ == "__main__":
    unittest.main()
