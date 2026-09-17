"""Several consoles flying ONE relic at once, each in their own suit.

The claim under test is the same one `test_boarding_site` makes about grid boarding, on
the other body model: six consoles, six suits, and nothing keyed by the relic. Plus the
part that is new here - a route that STAYS INSIDE the volume, which is the whole reason
the mode exists. A relic has no engine collision at all, so "it flew through the wall" is
the default behaviour and the route is the only thing preventing it.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import has_role, role

CONSOLES = [51, 52, 53, 54, 55, 56]


def _dist(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5

#: A relic shaped like an ELBOW: A, then B 1000 along x, then C 1000 along z from B.
#:
#: Bent on purpose. A straight corridor would prove nothing - passages are capsules, so a
#: run of chambers in a line is one continuous navigable tube and the direct course is
#: perfectly safe. The corner is what makes the route matter: the line from A to C passes
#: through the rock at (500, 0, 500), and `test_a_straight_line_would_NOT_have_been` pins
#: that, so the route test cannot pass on a relic where any course would do.
RELIC = "test_relic"


def _build_volume():
    V.volume_define(
        RELIC,
        chambers={"a": (0, 0, 0, 300), "b": (1000, 0, 0, 300), "c": (1000, 0, 1000, 300)},
        passages=[("a", "b", 60), ("b", "c", 60)],
    )


class _EvaBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        # RESUMED, not merely created. A paused sim never integrates, so `physics_tick`
        # is a no-op and a flight test reports "never arrived" while everything it is
        # actually testing is correct.
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        V.volume_clear()
        E.eva_clear()
        _build_volume()
        # A console has to be a real agent before anything can be stored ON it:
        # `set_inventory_value` resolves through `to_agent_list`, so a bare int that is
        # nobody silently writes nothing and every read answers None - which reads exactly
        # like "all six consoles share one suit", the bug these tests exist to disprove.
        from sbs_utils.gui import GuiClient
        for cid in CONSOLES:
            GuiClient(cid)
        # Points authored the way a relic authors them, without needing an .amd file:
        # `relic_points` reads the record store, so the store is what the test fills.
        from sbs_utils.procedural import amd_relics as R
        R._RELIC_RECORDS[RELIC] = {
            "key": RELIC, "loc": (0, 0, 0), "volume": RELIC,
            "points": {
                "mouth": [0, 0, 0, ["entrance"], "The Mouth"],
                "hall": [1000, 0, 0, ["room"], "The Long Hall"],
                "cradle": [1000, 0, 1000, ["relic_piece"], "The Cradle"],
            },
        }

    def tearDown(self):
        from sbs_utils.procedural import amd_relics as R
        R._RELIC_RECORDS.pop(RELIC, None)
        E.eva_clear()
        V.volume_clear()

    def suit_up(self, client_id, x=0, y=0, z=0, name="Crew"):
        who = lifeform_spawn(name, "", "boarding")
        suit = E.eva_suit_spawn(who, RELIC, x, y, z, hull="tsn_shuttle", side="tsn")
        E.eva_take(client_id, suit, RELIC, volume=RELIC)
        return who, suit


class TheSuitIsAShipButNotAPlayer(_EvaBase):
    def test_a_suit_wears_the_suit_role(self):
        _who, suit = self.suit_up(CONSOLES[0])
        self.assertIsNotNone(suit)
        self.assertTrue(has_role(suit, E.SUIT_ROLE))

    def test_a_suit_is_NOT_in_the_player_set(self):
        """The line the whole feature leans on.

        Without it six boarders are six more player ships: the enemy targets them, the
        end-game conditions count them, and the ship pickers offer them.
        """
        _who, suit = self.suit_up(CONSOLES[0])
        self.assertFalse(has_role(suit, "__player__"))
        self.assertNotIn(to_id(suit), set(role("__player__")))

    def test_the_suit_and_the_wearer_point_at_each_other(self):
        who, suit = self.suit_up(CONSOLES[0])
        self.assertEqual(E.eva_suit_of(who), to_id(suit))
        self.assertEqual(E.eva_lifeform_of(suit), to_id(who))

    def test_a_suit_gets_a_side(self):
        """No side means no relation to compare, so every contact draws unknown grey."""
        _who, suit = self.suit_up(CONSOLES[0])
        self.assertEqual(to_object(suit).side, "tsn")


class SixConsolesSixSuits(_EvaBase):
    def setUp(self):
        super().setUp()
        self.suits = {cid: self.suit_up(cid, x=cid, name="C%d" % cid)[1]
                      for cid in CONSOLES}

    def test_each_console_flies_its_own(self):
        seen = set()
        for cid in CONSOLES:
            mine = E.eva_my_suit(cid)
            self.assertEqual(mine, to_id(self.suits[cid]))
            seen.add(mine)
        self.assertEqual(len(seen), len(CONSOLES))

    def test_one_console_going_somewhere_moves_nobody_else(self):
        E.eva_goto(CONSOLES[0], "cradle")
        self.assertEqual(E.eva_dest(CONSOLES[0]), "cradle")
        for cid in CONSOLES[1:]:
            self.assertIsNone(E.eva_dest(cid))

    def test_releasing_one_console_leaves_the_rest_flying(self):
        E.eva_release(CONSOLES[0])
        self.assertIsNone(E.eva_my_suit(CONSOLES[0]))
        for cid in CONSOLES[1:]:
            self.assertIsNotNone(E.eva_my_suit(cid))


class TheRouteGoesTheWayTheRelicConnects(_EvaBase):
    def setUp(self):
        super().setUp()
        self.who, self.suit = self.suit_up(CONSOLES[0], x=0, y=0, z=0)

    def test_a_route_across_the_relic_passes_through_the_middle_room(self):
        """Asserts the SHAPE, not a leg count.

        The count is the navmesh's business and it changed once the route started going
        through doorways rather than room centres - more waypoints, each of them nearer
        the geometry. What has to be true is that the route bends round the corner, so
        that is what this measures: somewhere on it passes close to the middle room.
        """
        self.assertTrue(E.eva_goto(CONSOLES[0], "cradle"))
        dest, legs, _togo = E.eva_route(CONSOLES[0])
        self.assertEqual(dest, "cradle")
        self.assertGreater(legs, 1, "a straight line is not a route round a corner")
        from sbs_utils.procedural.inventory import get_inventory_value
        waypoints = get_inventory_value(CONSOLES[0], E.KEY_ROUTE, None)
        self.assertTrue(any(_dist(w, (1000, 0, 0)) < 400 for w in waypoints),
                        "no waypoint near the hall: %s" % (waypoints,))

    def test_the_last_waypoint_is_the_PLACE_not_the_room(self):
        E.eva_goto(CONSOLES[0], "cradle")
        from sbs_utils.procedural.inventory import get_inventory_value
        waypoints = get_inventory_value(CONSOLES[0], E.KEY_ROUTE, None)
        self.assertEqual(tuple(waypoints[-1]), (1000, 0, 1000))

    def test_every_waypoint_is_inside_the_volume(self):
        """The claim. A waypoint outside the volume is a course into the rock."""
        E.eva_goto(CONSOLES[0], "cradle")
        from sbs_utils.procedural.inventory import get_inventory_value
        for wp in get_inventory_value(CONSOLES[0], E.KEY_ROUTE, None):
            self.assertTrue(V.volume_contains(RELIC, wp),
                            "waypoint %r is outside the relic" % (wp,))

    def test_a_straight_line_would_NOT_have_been(self):
        """Pins the test against the bug: the direct line really does leave the volume.

        Without this the route test passes on a relic where any course would do.
        """
        self.assertFalse(V.volume_contains(RELIC, (500, 0, 500)))

    def test_somewhere_this_relic_does_not_have_is_refused(self):
        self.assertFalse(E.eva_goto(CONSOLES[0], "the moon"))
        self.assertIsNone(E.eva_dest(CONSOLES[0]))

    def test_stopping_drops_the_route(self):
        E.eva_goto(CONSOLES[0], "cradle")
        E.eva_stop(CONSOLES[0])
        self.assertEqual(E.eva_route(CONSOLES[0]), (None, 0, 0.0))


class FlyingIt(_EvaBase):
    def setUp(self):
        super().setUp()
        self.who, self.suit = self.suit_up(CONSOLES[0], x=0, y=0, z=0)

    def test_a_tick_points_the_suit_down_the_route(self):
        E.eva_goto(CONSOLES[0], "cradle")
        E.eva_tick()
        ds = to_object(self.suit).data_set
        self.assertEqual(ds.get("steeringToDirFlag", 0), 1)
        # Down the corridor, which is +x. The mock answers a never-set field with a typed
        # default, so this asserts the SIGN rather than merely that something was written.
        self.assertGreater(ds.get("steerToDirDX", 0), 0.5)

    def test_arriving_clears_the_route_and_says_so(self):
        from sbs_utils.procedural.signal import signal_emit  # noqa: F401  (documents the seam)
        E.eva_goto(CONSOLES[0], "mouth")     # already standing on it
        E.eva_tick()
        self.assertEqual(E.eva_route(CONSOLES[0]), (None, 0, 0.0))

    def test_a_console_with_no_route_is_not_flown(self):
        self.assertEqual(E.eva_flying(), [])
        E.eva_tick()
        self.assertEqual(E.eva_route_count(), 0)

    def test_a_suit_that_vanished_mid_route_stops_rather_than_raising(self):
        """A relic is torn down while somebody is still in it. That must not raise."""
        E.eva_goto(CONSOLES[0], "cradle")
        from sbs_utils.procedural.space_objects import delete_object
        delete_object(self.suit)
        E.eva_tick()
        self.assertEqual(E.eva_route(CONSOLES[0]), (None, 0, 0.0))


class ItStaysInsideTheWholeWay(_EvaBase):
    """The claim the mode exists for, flown rather than planned.

    THIS IS A REGRESSION TEST FOR A REAL BUG, and the bug is the reason the autopilot is
    not three lines. Planning a route through the chambers is not enough on its own: a
    suit leaving the entrance under full route throttle ARCS while it comes round to its
    first waypoint, and in a 160-unit passage the arc takes it clean out of the volume.
    Measured before the fix: `volume_depth` +41 at 20 seconds - outside the relic, on a
    perfectly correct course. `eva.ALIGN_OPEN` is what stopped it.

    Nothing short of flying it finds this. Every assertion about the ROUTE passes on the
    broken version, because the route was never what was wrong.
    """

    def setUp(self):
        super().setUp()
        self.who, self.suit = self.suit_up(CONSOLES[0], x=0, y=0, z=0)

    def _fly(self, seconds=420):
        """Run the real dispatcher and the real physics, and watch the wall."""
        from sbs_utils.tickdispatcher import TickDispatcher
        obj = to_object(self.suit)
        worst = -1e9
        arrived = None
        for step in range(int(seconds * 30)):
            sbs.physics_tick(1 / 30)
            TickDispatcher.dispatch_tick()
            worst = max(worst, V.volume_depth(RELIC, (obj.pos.x, obj.pos.y, obj.pos.z)))
            if E.eva_route(CONSOLES[0])[0] is None:
                arrived = step / 30.0
                break
        return worst, arrived, obj

    def test_the_suit_never_leaves_the_relic(self):
        E.eva_goto(CONSOLES[0], "cradle")
        worst, _arrived, _obj = self._fly()
        self.assertLess(worst, 0.0,
                        "the suit was OUTSIDE the relic at its worst point "
                        "(depth %+.1f); a positive depth is through the wall" % worst)

    def test_and_it_gets_there(self):
        """A suit that never moves also never leaves the volume, so the containment
        assertion above needs this one beside it or it passes on a parked ship."""
        E.eva_goto(CONSOLES[0], "cradle")
        _worst, arrived, obj = self._fly()
        self.assertIsNotNone(arrived, "never arrived within the time given")
        self.assertLess(_dist((obj.pos.x, obj.pos.y, obj.pos.z), (1000, 0, 1000)), 120,
                        "stopped at (%.0f, %.0f), not the cradle" % (obj.pos.x, obj.pos.z))


class WhereYouCanGo(_EvaBase):
    def setUp(self):
        super().setUp()
        # OFF the mouth, not on it. A place you are standing on is not a destination and
        # is left out of the list, so a fixture parked exactly on one is testing the
        # exclusion rather than the listing. 150 is well inside the 300 chamber and well
        # outside the 60 arrival radius.
        self.who, self.suit = self.suit_up(CONSOLES[0], x=150, y=0, z=0)

    def test_the_list_carries_the_authored_label(self):
        names = {row[0]: row[1] for row in E.eva_points(CONSOLES[0])}
        self.assertEqual(names["cradle"], "The Cradle")

    def test_the_list_is_nearest_first(self):
        order = [row[0] for row in E.eva_points(CONSOLES[0])]
        self.assertEqual(order, ["mouth", "hall", "cradle"])

    def test_a_role_narrows_it(self):
        only = [row[0] for row in E.eva_points(CONSOLES[0], role_name="entrance")]
        self.assertEqual(only, ["mouth"])

    def test_a_suit_REVEALS_places_as_it_flies(self):
        """The Nav list grows as the party explores - that is the whole feature.

        Reported from a bridge: "the nav still only lists the mouth". A marker lights
        when a player comes within range, and the reveal tick watched `role("__player__")`
        only - which a suit is deliberately NOT in. So a party could fly a ruin end to end
        and light up nothing, leaving the list at whatever their SHIP passed on the way in.
        """
        from sbs_utils.procedural import amd_relics as R
        from sbs_utils.vec import Vec3
        # Arm a marker at the cradle that nobody has reached yet.
        R._ARMED[("marker", RELIC, "cradle")] = {
            "done": True, "id": None, "pos": (1000, 0, 1000),
            "shown": False, "reveal": 1200.0}
        # `revealed_only=True` EXPLICITLY, because it is no longer the default: gating the
        # Nav list on reveal deadlocked a shipped relic (see `eva_points`). The reveal
        # mechanism itself still has to work - it is what lights the marker - so this test
        # asks for it by name.
        self.assertNotIn("cradle",
                         [r[0] for r in E.eva_points(CONSOLES[0], revealed_only=True)])
        # Fly the SUIT to WITHIN REVEAL RANGE of it - no player ship involved anywhere.
        # Not ONTO it: a place you are standing on is never offered as a destination, so
        # parking on the marker would light it and then hide it again for a different
        # reason, and the test would fail while the feature worked.
        to_object(self.suit).pos = Vec3(700, 0, 700)
        R._relic_reveal_tick()
        self.assertIn("cradle",
                      [r[0] for r in E.eva_points(CONSOLES[0], revealed_only=True)],
                      "a suit flying to a place must light its marker")
        R._ARMED.pop(("marker", RELIC, "cradle"), None)

    def test_an_ARMED_relic_still_offers_somewhere_to_go(self):
        """The deadlock, pinned. Reported twice from a bridge: "nav Option: The mouth".

        Arm every point the way a shipped relic arms them, none of them reached. If the
        list gates on reveal, the only place offered is the one the SHIP passed on the way
        in - and the only way to reveal a second is to fly to it, which the list will not
        offer. Every test relic before this one was UNARMED, which is why the unit tests
        were green while the mode was unplayable.
        """
        from sbs_utils.procedural import amd_relics as R
        for name, pos in (("mouth", (0, 0, 0)), ("hall", (1000, 0, 0)),
                          ("cradle", (1000, 0, 1000))):
            R._ARMED[("marker", RELIC, name)] = {
                "done": True, "id": None, "pos": pos, "shown": name == "mouth",
                "reveal": 1200.0}
        try:
            self.assertEqual([r[0] for r in E.eva_points(CONSOLES[0])],
                             ["mouth", "hall", "cradle"],
                             "an armed relic must still offer its far rooms")
        finally:
            for name in ("mouth", "hall", "cradle"):
                R._ARMED.pop(("marker", RELIC, name), None)

    def test_points_with_no_marker_are_listed(self):
        """A relic whose contents were never armed has no markers at all.

        Answering "not revealed" for those would show an empty list on a relic that does
        not use the reveal mechanism, which is most of them in a test or a small mission.
        """
        self.assertEqual(len(E.eva_points(CONSOLES[0], revealed_only=True)), 3)

    def test_where_names_the_chamber(self):
        self.assertEqual(E.eva_where(CONSOLES[0]), "a")

    def test_a_console_with_no_suit_is_adrift(self):
        self.assertEqual(E.eva_where(CONSOLES[1]), "adrift")

    def test_where_you_are_STANDING_is_not_offered(self):
        """Reported from a bridge: picking it made two buttons appear and then go away.

        Choosing the place you are already at sets a course, the screen grows an
        "Under way" row and a Hold station button, and the next tick notices you are
        inside the arrival radius and removes them - a flicker with no cause a player
        can see. You cannot fly to where you are standing, so it is not on the menu.
        """
        from sbs_utils.vec import Vec3
        to_object(self.suit).pos = Vec3(0, 0, 0)          # stand on the mouth
        offered = [row[0] for row in E.eva_points(CONSOLES[0])]
        self.assertNotIn("mouth", offered)
        self.assertIn("hall", offered)
        self.assertFalse(E.eva_goto(CONSOLES[0], "mouth"),
                         "a course to where you already are must be refused")


class TheResetLetsGo(_EvaBase):
    def test_clearing_takes_the_suits_and_the_consoles(self):
        for cid in CONSOLES:
            self.suit_up(cid, x=cid)
        E.eva_goto(CONSOLES[0], "cradle")
        self.assertEqual(E.eva_suit_count(), len(CONSOLES))
        E.eva_clear()
        self.assertEqual(E.eva_suit_count(), 0)
        self.assertEqual(E.eva_route_count(), 0)
        for cid in CONSOLES:
            self.assertIsNone(E.eva_my_suit(cid))

    def test_clearing_leaves_the_lifeform_alone(self):
        """The cast belongs to `boarding.py`. This owns only the bodies."""
        who, _suit = self.suit_up(CONSOLES[0])
        E.eva_clear()
        self.assertIsNotNone(to_object(who))
        self.assertIsNone(E.eva_suit_of(who))

    def test_the_tick_does_not_outlive_the_mission(self):
        self.suit_up(CONSOLES[0])
        E.eva_goto(CONSOLES[0], "cradle")
        self.assertIsNotNone(Agent.SHARED.get_inventory_value(E._TICK_KEY, None))
        E.eva_clear()
        self.assertIsNone(Agent.SHARED.get_inventory_value(E._TICK_KEY, None))


if __name__ == "__main__":
    unittest.main()


class ARouteItCannotFindIsRefused(_EvaBase):
    """A relic has no engine collision, so "fly at it and hope" means fly THROUGH it.

    Reported from a bridge 2026-09-17: "it seems like it flies directly toward it which
    can take it through walls." The cause was in `volume_route`, which answered with the
    straight line in all four of its failure cases - so the caller could not tell a clean
    one-leg run from "I could not find a way", and flew both.
    """

    def setUp(self):
        super().setUp()
        self.who, self.suit = self.suit_up(CONSOLES[0], x=0, y=0, z=0)
        # A room with no way into it: a chamber off on its own, and a place inside it.
        V.volume_define(RELIC,
                        chambers={"a": (0, 0, 0, 300), "b": (1000, 0, 0, 300),
                                  "c": (1000, 0, 1000, 300),
                                  "vault": (9000, 0, 9000, 300)},
                        passages=[("a", "b", 60), ("b", "c", 60)])
        from sbs_utils.procedural import amd_relics as R
        R._RELIC_RECORDS[RELIC]["points"]["vault"] = [9000, 0, 9000, ["relic_piece"],
                                                      "The Sealed Vault"]
        self.addCleanup(R._RELIC_RECORDS[RELIC]["points"].pop, "vault", None)

    def test_it_refuses_rather_than_flying_through_the_rock(self):
        self.assertFalse(E.eva_goto(CONSOLES[0], "vault"))
        self.assertEqual(E.eva_route(CONSOLES[0])[0], None,
                         "a refused destination must leave the suit holding station")

    def test_and_says_which_place_it_could_not_reach(self):
        E.eva_goto(CONSOLES[0], "vault")
        self.assertEqual(E.eva_no_way(CONSOLES[0]), "vault")

    def test_a_reachable_place_still_goes_and_clears_it(self):
        E.eva_goto(CONSOLES[0], "vault")
        self.assertTrue(E.eva_goto(CONSOLES[0], "cradle"))
        self.assertIsNone(E.eva_no_way(CONSOLES[0]))

    def test_the_router_itself_can_say_no(self):
        self.assertEqual(
            V.volume_route(RELIC, (0, 0, 0), (9000, 0, 9000), waypoints=[], strict=True),
            [], "strict must answer [] rather than the straight line")

    def test_but_the_old_answer_is_unchanged_for_everyone_else(self):
        """The default stays the guess - a caller that only wants a heading is better
        served by one than by nothing, and every existing caller expects it."""
        self.assertEqual(
            V.volume_route(RELIC, (0, 0, 0), (9000, 0, 9000), waypoints=[]),
            [(9000, 0, 9000)])


class HowHardYouFly(_EvaBase):
    def setUp(self):
        super().setUp()
        self.who, self.suit = self.suit_up(CONSOLES[0], x=0, y=0, z=0)

    def test_it_cruises_unless_told_otherwise(self):
        self.assertEqual(E.eva_speed(CONSOLES[0]), "Cruise")
        self.assertEqual(E.eva_speed_value(CONSOLES[0]), E.CRUISE)

    def test_a_console_can_pick_another(self):
        E.eva_speed(CONSOLES[0], "Fast")
        self.assertEqual(E.eva_speed(CONSOLES[0]), "Fast")
        self.assertGreater(E.eva_speed_value(CONSOLES[0]), E.CRUISE)

    def test_it_is_PER_CONSOLE(self):
        """Six suits in one ruin are six people deciding how fast to take a corner."""
        self.suit_up(CONSOLES[1], x=0, y=0, z=0)
        E.eva_speed(CONSOLES[0], "Careful")
        self.assertEqual(E.eva_speed(CONSOLES[1]), "Cruise")

    def test_a_name_it_does_not_know_is_ignored(self):
        E.eva_speed(CONSOLES[0], "ludicrous")
        self.assertEqual(E.eva_speed(CONSOLES[0]), "Cruise")
