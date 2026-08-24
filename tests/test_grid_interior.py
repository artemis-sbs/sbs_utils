"""Deferred, phased engineering interiors.

WHY A SHIP'S INTERIOR IS NOT BUILT WHEN IT SPAWNS. Player ships are created long before
anyone picks a map - LegendaryMissions builds the whole roster at server-console start - so
a `//spawn` route that builds an interior builds one for EVERY slot on whatever hull the
roster happened to name. Then the roster culls to PLAYER_COUNT and parks the rest, a game
code may apply a hull, and the map body may re-hull again. Measured on one Trek trial: 110
objects built for a hull nobody flew, then 124 built twice more for the hull they did.

So a request is RECORDED and the build happens once the hulls are final, reading the hull at
BUILD time.

WHAT THESE TESTS PIN, in the order they would go wrong:

  * **A request builds nothing.** If it did, the whole thing is just the old behavior with
    extra steps.
  * **The deferred build EQUALS the inline one.** A build that runs but produces fewer rooms
    is worse than no change - Engineering half-works and nobody notices.
  * **A re-hull between request and build wins.** This is the entire point.
  * **flush() DRAINS.** The first queued item for a ship is the planner, whose job is to
    queue that hull's slices; a single flush runs the planner and returns with all the real
    work still pending. That shipped broken and reported a ship with ZERO grid objects.

    python -m unittest tests.test_grid_interior
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as mock
from tests.reset_helper import reset_mock

from sbs_utils.procedural import internal_damage as ID
from sbs_utils.procedural.grid import grid_objects
from sbs_utils.procedural.internal_damage import (
    grid_interior_arm, grid_interior_flush, grid_interior_is_armed,
    grid_interior_pending, grid_interior_request, grid_interior_reset,
    grid_rebuild_grid_objects)
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.spawn import player_spawn


def _plan(ship, w, h):
    """A rectangular floor plan of `w` x `h` cargo rooms for `ship`."""
    rows = "\n".join("c" * w for _ in range(h))
    return f"ship: {ship}\nsize: {w}x{h}\nlegend:\n  c: cargo\n---\n{rows}"


class GridInteriorTests(unittest.TestCase):

    BIG = "tsn_battle_cruiser"
    SMALL = "tsn_light_cruiser"

    def setUp(self):
        reset_mock(mock)
        grid_interior_reset()
        # Two hulls with DIFFERENT room counts, so "it built the right one" is answerable.
        self._merge(_plan(self.BIG, 6, 4))      # 24 rooms
        self._merge(_plan(self.SMALL, 3, 2))    # 6 rooms

    def _merge(self, text):
        from sbs_utils.procedural.grid import grid_merge_ascii
        grid_merge_ascii(text, "test")

    def _ship(self, hull, x=0, name="Probe"):
        return to_id(player_spawn(x, 0, 0, name, "tsn", hull))

    def _count(self, ship_id):
        return len(grid_objects(ship_id) or [])

    # --- a request builds nothing --------------------------------------------

    def test_a_request_creates_no_grid_objects(self):
        s = self._ship(self.BIG)
        self.assertTrue(grid_interior_request(s))
        self.assertEqual(0, self._count(s),
                         "the request BUILT something - the deferral does nothing")
        self.assertFalse(grid_interior_is_armed())
        self.assertEqual(1, grid_interior_pending())

    def test_requesting_the_same_ship_twice_builds_once(self):
        s = self._ship(self.BIG)
        grid_interior_request(s)
        grid_interior_request(s)
        grid_interior_flush()
        inline = self._ship(self.BIG, x=9000, name="Inline")
        grid_rebuild_grid_objects(inline)
        self.assertEqual(self._count(inline), self._count(s),
                         "asking twice built twice")

    # --- and then builds the same thing the inline path would ----------------

    def test_the_deferred_build_equals_the_inline_one(self):
        """Two SHIPS, not one cleared and reused: deleting grid objects tombstones them,
        so a clear-and-rebuild in the same frame reads back the old count and a probe
        written that way reports success while proving nothing."""
        inline = self._ship(self.BIG, x=0, name="Inline")
        deferred = self._ship(self.BIG, x=9000, name="Deferred")
        grid_rebuild_grid_objects(inline)
        baseline = self._count(inline)
        self.assertGreater(baseline, 0, "the inline baseline built nothing")

        grid_interior_request(deferred)
        self.assertEqual(0, self._count(deferred))
        grid_interior_arm()
        grid_interior_flush()
        self.assertEqual(baseline, self._count(deferred))

    def test_flush_drains_work_the_flushed_work_itself_queued(self):
        """The first item queued for a ship is the PLANNER, and its whole job is to queue
        that hull's room slices. A single flush runs the planner and returns with every
        real item still pending - measured as 1 run, 8 pending, and a ship with zero grid
        objects."""
        s = self._ship(self.BIG)
        grid_interior_request(s)
        grid_interior_arm()
        grid_interior_flush()
        self.assertEqual(0, grid_interior_pending(),
                         "flush left queued work behind")
        self.assertGreater(self._count(s), 0)

    # --- the re-hull, which is the whole point -------------------------------

    def test_a_re_hull_between_request_and_build_wins(self):
        s = self._ship(self.SMALL, name="Rehulled")
        grid_interior_request(s)
        to_object(s).art_id = self.BIG          # the map decides what it is really flying
        grid_interior_flush()

        control = self._ship(self.BIG, x=9000, name="Control")
        grid_rebuild_grid_objects(control)
        self.assertEqual(self._count(control), self._count(s),
                         "built the interior it had when it ASKED, not the one it needs")

    # --- a ship nobody will fly -----------------------------------------------

    def test_a_parked_ship_is_dropped_rather_than_built(self):
        """The roster parks every slot past PLAYER_COUNT - suspended to standby, hull
        blanked. Building for one means walking the whole layout lookup to discover there
        is no floor plan for `invisible`, then saying so loudly, once per parked hull.
        Seven per run on a default roster."""
        import sys
        s = self._ship(self.BIG)
        grid_interior_request(s)
        sys.modules["sbs"].push_to_standby_list_id(s)
        grid_interior_flush()
        self.assertEqual(0, self._count(s))

    def test_a_deleted_ship_is_dropped_rather_than_raising(self):
        s = self._ship(self.BIG)
        grid_interior_request(s)
        to_object(s).delete_object()
        grid_interior_flush()          # must not raise
        self.assertEqual(0, grid_interior_pending())

    # --- arming ---------------------------------------------------------------

    def test_a_request_after_arming_is_queued_immediately(self):
        """A mid-game refit or a late player ship must not wait for anyone to re-arm."""
        grid_interior_arm()
        s = self._ship(self.BIG)
        grid_interior_request(s)
        grid_interior_flush()
        self.assertGreater(self._count(s), 0)

    def test_arm_reports_how_many_it_released(self):
        a = self._ship(self.BIG, x=0, name="A")
        b = self._ship(self.BIG, x=9000, name="B")
        grid_interior_request(a)
        grid_interior_request(b)
        self.assertEqual(2, grid_interior_arm())

    # --- reset ledger ---------------------------------------------------------

    def test_reset_drops_queued_work_and_disarms(self):
        """A queued interior belongs to the ship that asked for it, and after a mission
        reset both are gone. Disarming matters too - run 2 must defer again until ITS
        hulls settle."""
        s = self._ship(self.BIG)
        grid_interior_request(s)
        grid_interior_arm()
        self.assertTrue(grid_interior_is_armed())
        grid_interior_reset()
        self.assertEqual(0, grid_interior_pending())
        self.assertFalse(grid_interior_is_armed())

    def test_the_reset_ledger_probe_sees_pending_work(self):
        s = self._ship(self.BIG)
        grid_interior_request(s)
        self.assertGreater(grid_interior_pending(), 0)
        reset_mock(mock)
        self.assertEqual(0, grid_interior_pending())


if __name__ == "__main__":
    unittest.main()
