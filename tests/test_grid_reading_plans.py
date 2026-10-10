"""A floor plan can be KEPT FOR READING without becoming the hull's interior
(procedural/grid.py `grid_plan_ascii`).

LegendaryMissions merges a race's `.grid` plans only when the race is PLAYABLE, because
the merge is not free of consequences: the grid data it writes is what an interior is
built from, what `grid_count_grid_data` counts a hull's fighter and shuttle bays from,
and what `grid_hull_has_role` answers from. So the raiders' hulls had no plan at all, and
a surrendered Kralien could not be boarded.

`grid_plan_ascii` keeps the plan where ONLY a reader asks for it - a boarding party's
deck (`boarding_deck_plan`) - and leaves every one of those other answers exactly as it
was.

    python -m unittest tests.test_grid_reading_plans
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import copy
import sys
import unittest

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.procedural import boarding_deckplan as D
from sbs_utils.procedural import grid as G
from sbs_utils.procedural.internal_damage import grid_count_grid_data

# A hull nothing else has: rooms on a hallway, with a bay that has the `fighter` role.
READING_PLAN = """ship: reading_test_raider
size: 6x4
legend:
  w: warp
  b: boat-bay / room,bay,fighter
  q: crew-quarters
---
ww..bb
ww..bb
..qq..
..qq..
"""

# The same hull key the engine's own data has rooms for.
READING_PLAN_TSN = READING_PLAN.replace("reading_test_raider", "tsn_light_cruiser")


class ReadingPlanTests(unittest.TestCase):
    def setUp(self):
        reset_mission_state()
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        self.addCleanup(reset_mission_state)
        self.before = copy.deepcopy(G.grid_get_grid_data())

    def test_it_is_callable_from_mast(self):
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        for name in ("grid_plan_ascii", "grid_get_plan_layout", "grid_get_plan_open_cells"):
            self.assertTrue(callable(MastGlobals.globals.get(name)), name)

    def test_a_kept_plan_gives_the_hull_a_deck(self):
        self.assertFalse(D.boarding_deck_has_plan("reading_test_raider"))
        self.assertIsNone(D.boarding_deck_plan("reading_test_raider"))
        kept = G.grid_plan_ascii(READING_PLAN, "races")
        self.assertIsNotNone(kept)
        self.assertTrue(D.boarding_deck_has_plan("reading_test_raider"))
        plan = D.boarding_deck_plan("reading_test_raider")
        self.assertEqual(plan["source"], "grid text")
        self.assertEqual(plan["cells"][(0, 0)], "warp")
        self.assertEqual(plan["cells"][(2, 0)], "")              # the hallway the text drew
        self.assertEqual((plan["w"], plan["h"]), (6, 4))

    def test_it_is_NOT_the_hulls_interior(self):
        G.grid_plan_ascii(READING_PLAN, "races")
        # The grid data - what an interior is built from - has not heard of it.
        self.assertEqual(G.grid_get_grid_data(), self.before)
        self.assertNotIn("reading_test_raider", G.grid_get_grid_data())
        self.assertIsNone(G.grid_get_layout("reading_test_raider"))
        self.assertIsNone(G.grid_get_open_cells("reading_test_raider"))
        # ... so nothing counts bays from it, and nothing asks it for a role.
        self.assertEqual(grid_count_grid_data("reading_test_raider", "fighter", 0), 0)
        self.assertFalse(G.grid_hull_has_role("reading_test_raider", "fighter"))

    def test_the_same_text_MERGED_does_change_those_answers(self):
        """Why LegendaryMissions cannot simply merge every race's plans."""
        G.grid_merge_ascii(READING_PLAN, "races")
        self.assertIn("reading_test_raider", G.grid_get_grid_data())
        self.assertEqual(grid_count_grid_data("reading_test_raider", "fighter", 0), 4)

    def test_a_hull_with_an_interior_keeps_it_and_the_deck_is_drawn_from_that(self):
        had = copy.deepcopy(G.grid_get_layout("tsn_light_cruiser"))
        self.assertTrue(had, "the engine's data should have this hull's rooms")
        G.grid_plan_ascii(READING_PLAN_TSN, "races")
        self.assertEqual(G.grid_get_layout("tsn_light_cruiser"), had)
        self.assertEqual(G.grid_get_plan_layout("tsn_light_cruiser"), had)
        names = set(D.boarding_deck_plan("tsn_light_cruiser")["cells"].values())
        self.assertNotIn("boat-bay", names)

    def test_a_plan_merged_later_takes_over_from_the_kept_one(self):
        G.grid_plan_ascii(READING_PLAN, "races")
        G.grid_merge_ascii(READING_PLAN.replace("boat-bay", "launch-bay"), "a_mod")
        names = set(D.boarding_deck_plan("reading_test_raider")["cells"].values())
        self.assertIn("launch-bay", names)
        self.assertNotIn("boat-bay", names)

    def test_text_that_cannot_be_read_is_said_and_keeps_nothing(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertIsNone(G.grid_plan_ascii("", "races"))
            self.assertIsNone(G.grid_plan_ascii("not a plan at all", "races"))
        self.assertEqual(G.grid_plans_kept(), 0)

    def test_the_mission_reset_forgets_them_and_the_ledger_knows(self):
        G.grid_plan_ascii(READING_PLAN, "races")
        self.assertEqual(G.grid_plans_kept(), 1)
        reset_mission_state()
        self.assertEqual(G.grid_plans_kept(), 0)
        self.assertFalse(D.boarding_deck_has_plan("reading_test_raider"))
        self.assertNotIn("grid reading plans", dict(reset_mission_audit()))


if __name__ == "__main__":
    unittest.main()
