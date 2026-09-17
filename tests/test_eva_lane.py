"""The flight envelope, and the record of where a crew has been.

TWO THINGS, and they share a fixture.

**The envelope.** `RAIL_ROPE` (140), `DRIFT_MAX` (90) and `ARRIVE_RADIUS` (120) were flat
numbers while the corridor the router proved clear was twenty units - so the thing being
flown was up to seven times wider than the only space anyone had proved, and the overflow
went into the rock. They are fractions of the current leg's own clearance now.

The worst of the three was arrival: counting a waypoint as reached 120 units out means
the suit starts its turn 120 units short of the node and never flies the leg at all - it
leaves early and crosses whatever is inside the corner.

**Visited.** A ruin is a map you are drawing, and every room used to read the same whether
the crew cleared it an hour ago or had never been near it.

    python -m unittest tests.test_eva_lane
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
from sbs_utils.procedural.inventory import set_inventory_value

CID = 61
RELIC = "__eva_lane__"


class _Base(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        V.volume_clear()
        E.eva_clear()
        GuiClient(CID)


class LegClearanceTests(_Base):
    def test_it_measures_the_pinch_not_the_ends(self):
        """Both ends of a leg are nodes and therefore already clear - the interesting
        number is the corner it clips on the way past."""
        # The rooms must NOT meet, or the middle of the leg is still deep inside a wide
        # room and there is no pinch to find. West stops at -200, east starts at 200, and
        # only the throat spans the gap between them.
        V.volume_define(RELIC, boxes={"west": (-800, 0, 0, 600, 400, 400),
                                      "throat": (0, 0, 0, 300, 40, 40),
                                      "east": (800, 0, 0, 600, 400, 400)})
        got = E._eva_leg_clearance(RELIC, (-600.0, 0.0, 0.0), (600.0, 0.0, 0.0))
        self.assertIsNotNone(got)
        self.assertLessEqual(got, 40.0, "it missed the throat between the two rooms")

    def test_an_unknown_volume_is_none_not_an_error(self):
        self.assertIsNone(E._eva_leg_clearance("nope", (0, 0, 0), (1, 0, 0)))

    def test_a_missing_end_is_none(self):
        V.volume_define(RELIC, boxes={"hall": (0, 0, 0, 900, 400, 400)})
        self.assertIsNone(E._eva_leg_clearance(RELIC, None, (1, 0, 0)))


class RoomScalingTests(_Base):
    """`_eva_room` is what turns a ceiling into what the current leg can afford."""

    def test_an_unmeasured_leg_keeps_the_old_ceiling(self):
        """THE BACK-COMPATIBILITY GUARANTEE. A route flown before a web existed, or a
        relic built in code, must not be made worse than it was."""
        self.assertEqual(E._eva_room(CID, E.RAIL_ROPE, E.ROPE_FRACTION), E.RAIL_ROPE)
        self.assertEqual(E._eva_room(CID, E.ARRIVE_RADIUS, E.ARRIVE_FRACTION),
                         E.ARRIVE_RADIUS)

    def test_a_tight_leg_shrinks_the_rope(self):
        set_inventory_value(CID, E.KEY_LEG_CLEAR, 50.0)
        self.assertEqual(E._eva_room(CID, E.RAIL_ROPE, E.ROPE_FRACTION), 25.0)

    def test_a_wide_leg_is_still_capped_by_the_ceiling(self):
        """An open hall does not license an unbounded rope - the ceiling is a judgement
        about how far off course is acceptable at all."""
        set_inventory_value(CID, E.KEY_LEG_CLEAR, 100000.0)
        self.assertEqual(E._eva_room(CID, E.RAIL_ROPE, E.ROPE_FRACTION), E.RAIL_ROPE)

    def test_a_leg_in_the_rock_never_goes_negative(self):
        set_inventory_value(CID, E.KEY_LEG_CLEAR, -400.0)
        self.assertEqual(E._eva_room(CID, E.RAIL_ROPE, E.ROPE_FRACTION), 0.0)

    def test_arrival_has_a_floor(self):
        """A radius that shrinks to nothing means a suit can never register reaching a
        waypoint - it would orbit it until the stall detector gave up and replanned."""
        set_inventory_value(CID, E.KEY_LEG_CLEAR, 2.0)
        reach = max(E.ARRIVE_MIN,
                    E._eva_room(CID, E.ARRIVE_RADIUS, E.ARRIVE_FRACTION))
        self.assertEqual(reach, E.ARRIVE_MIN)

    def test_a_tight_leg_stops_the_corner_cut(self):
        """The number that matters: on a 60-unit leg the suit must fly to its waypoint,
        not begin turning 120 units short of it."""
        set_inventory_value(CID, E.KEY_LEG_CLEAR, 60.0)
        reach = max(E.ARRIVE_MIN,
                    E._eva_room(CID, E.ARRIVE_RADIUS, E.ARRIVE_FRACTION))
        self.assertLess(reach, E.ARRIVE_RADIUS)


class RopeTests(_Base):
    def test_the_rope_length_is_honoured(self):
        """Inside the rope the aim is untouched; beyond it the aim blends back to the
        leg. A shorter rope has to actually pull sooner."""
        leg = (0.0, 0.0, 0.0)
        aim = (1000.0, 0.0, 0.0)
        near = (500.0, 60.0, 0.0)
        self.assertEqual(E._eva_rope(near, aim, leg, rope=140.0), aim)
        pulled = E._eva_rope(near, aim, leg, rope=25.0)
        self.assertNotEqual(pulled, aim)

    def test_no_leg_means_no_rope(self):
        aim = (1000.0, 0.0, 0.0)
        self.assertEqual(E._eva_rope((0.0, 900.0, 0.0), aim, None), aim)


class VisitedTests(_Base):
    def test_nothing_is_visited_to_begin_with(self):
        self.assertFalse(E.eva_visited(CID, "hold", RELIC))
        self.assertEqual(E.eva_visited_names(CID, RELIC), ())

    def test_arriving_records_it(self):
        self.assertTrue(E.eva_visit_note(CID, "hold", RELIC))
        self.assertTrue(E.eva_visited(CID, "hold", RELIC))
        self.assertEqual(E.eva_visited_names(CID, RELIC), ("hold",))

    def test_it_is_recorded_once(self):
        E.eva_visit_note(CID, "hold", RELIC)
        self.assertFalse(E.eva_visit_note(CID, "hold", RELIC))
        self.assertEqual(E.eva_visited_names(CID, RELIC), ("hold",))

    def test_relics_are_kept_apart(self):
        """Two ruins can name a room the same thing, and having been in one is not
        having been in the other."""
        E.eva_visit_note(CID, "hold", RELIC)
        self.assertFalse(E.eva_visited(CID, "hold", "another_relic"))

    def test_consoles_are_kept_apart(self):
        GuiClient(62)
        E.eva_visit_note(CID, "hold", RELIC)
        self.assertFalse(E.eva_visited(62, "hold", RELIC))

    def test_an_empty_name_records_nothing(self):
        self.assertFalse(E.eva_visit_note(CID, "", RELIC))
        self.assertEqual(E.eva_visited_names(CID, RELIC), ())


class SeenTests(_Base):
    def test_a_point_with_no_marker_is_not_seen(self):
        """THE TRAP. `relic_point_revealed` answers True for a point that has no marker,
        which is right for gating destinations and useless as a record of where anyone
        has been - without the marker test, every place in an unarmed relic reads as
        already visited."""
        from sbs_utils.procedural.amd_relics import relic_point_revealed
        self.assertTrue(relic_point_revealed(RELIC, "hold"))
        self.assertFalse(E.eva_seen(CID, "hold", RELIC))

    def test_no_relic_is_not_seen(self):
        self.assertFalse(E.eva_seen(CID, "hold", None))


class NavMarkTests(unittest.TestCase):
    """What the row actually prints. ASCII, because the engine draws no other kind."""

    def _mark(self, item):
        from sbs_utils.procedural.gui.xess import _nav_mark
        return _nav_mark(item)

    def test_visited_beats_seen(self):
        from sbs_utils.procedural.gui.xess import NAV_MARK_VISITED
        self.assertEqual(self._mark(("k", "Hold", True, True)),
                         NAV_MARK_VISITED)

    def test_seen_but_not_entered(self):
        from sbs_utils.procedural.gui.xess import NAV_MARK_SEEN
        self.assertEqual(self._mark(("k", "Hold", False, True)),
                         NAV_MARK_SEEN)

    def test_new_is_blank(self):
        from sbs_utils.procedural.gui.xess import NAV_MARK_NEW
        self.assertEqual(self._mark(("k", "Hold", False, False)),
                         NAV_MARK_NEW)

    def test_a_short_row_still_renders(self):
        """A row from a caller that predates the marks draws a blank rather than raising.

        `eva_points` itself stayed a THREE-tuple: callers destructure it, so appending
        flags there broke the Nav app and five tests at once. The flags are composed in
        the nav app, where the renderer needs them."""
        from sbs_utils.procedural.gui.xess import NAV_MARK_NEW
        self.assertEqual(self._mark(("k", "Hold")), NAV_MARK_NEW)

    def test_the_marks_are_ascii_and_line_up(self):
        from sbs_utils.procedural.gui.xess import (NAV_MARK_NEW, NAV_MARK_SEEN,
                                                   NAV_MARK_VISITED)
        for mark in (NAV_MARK_VISITED, NAV_MARK_SEEN, NAV_MARK_NEW):
            mark.encode("ascii")
            self.assertEqual(len(mark), len(NAV_MARK_NEW))


if __name__ == "__main__":
    unittest.main()
