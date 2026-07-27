"""Tests for a2x_declare_sides -- specifically that its ENGINE-side writes are complete
and repeatable.

The link-graph half of side setup (side_are_enemies and friends) is covered by
tests/test_sides.py and the A2xTestRange conformance map. What is pinned here is the other
half: what actually reaches sim.set_side_relationship / set_side_icon_color /
set_diplomacy_color, because that half is what the 2D map draws from and it fails
SILENTLY when it goes missing -- contacts render as UNKNOWN (grey) with the link graph
still perfectly correct, so nothing in the scripting layer notices.

The regression this guards: the self-ally (same side = ALLIED) relation was only ever
issued by side_ensure, i.e. exactly once, when the side was first created. Re-declaring
therefore could not repair an engine table that lost the first declaration -- which is
what happens whenever the declaration shares a frame with sim_create(), since
FrameContext.context.sim still points at the pre-sim_create simulation for the rest of
that event and every sim.* write lands on a dead handle.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.a2x.sides import declare_sides, set_diplomacy_colors, side_key


def _rel(sim, a, b):
    """The relation the engine holds for a -> b, in that order (the table is directional)."""
    return sim.side_relations.get((a, b))


class A2xDeclareSidesEngineTableTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_declare_writes_the_engine_tables(self):
        declare_sides([0, 1, 2])
        self.assertEqual(_rel(self.sim, "enemy", "friendly"), sbs.DIPLOMACY.HOSTILE)
        # sideValue 0 is "no side": present, but nobody's enemy.
        self.assertEqual(_rel(self.sim, "neutral", "enemy"), sbs.DIPLOMACY.NEUTRAL)
        self.assertEqual(self.sim.side_icon_colors["enemy"], "#F00")
        self.assertEqual(self.sim.side_icon_colors["friendly"], "#07F")
        self.assertEqual(self.sim.diplomacy_colors[int(sbs.DIPLOMACY.HOSTILE)], "#F00")
        self.assertEqual(self.sim.diplomacy_colors[int(sbs.DIPLOMACY.NEUTRAL)], "#077")

    def test_relations_are_written_in_BOTH_directions(self):
        """The engine's table is directional; colouring reads viewer-side -> contact-side.

        This is the bug that cost the most to find. a2x declared each pair exactly once, as
        (enemy, friendly). Every scripting-level check passed, the engine accepted the call,
        and the objects carried the right tags -- but a player on "friendly" looked up
        friendly -> enemy, found nothing, and every enemy drew grey. LegendaryMissions only
        looked right because maps/sides.amd declares the hostility on BOTH sides, so it
        wrote both directions by accident of authoring. The mock hid it completely by
        keying the table with a frozenset.
        """
        declare_sides([1, 2])
        self.assertEqual(_rel(self.sim, "enemy", "friendly"), sbs.DIPLOMACY.HOSTILE)
        self.assertEqual(_rel(self.sim, "friendly", "enemy"), sbs.DIPLOMACY.HOSTILE,
                         "the viewer-side -> contact-side direction is the one that colours")

    def test_self_ally_reaches_the_engine(self):
        declare_sides([1, 2])
        for v in (1, 2):
            k = side_key(v)
            self.assertEqual(_rel(self.sim, k, k), sbs.DIPLOMACY.ALLIED,
                             f"{k} not ALLIED to itself in the engine table")

    def test_redeclare_repairs_a_wiped_engine_table(self):
        """The re-assert loop a converted mission runs must restore EVERYTHING.

        Simulates the writes having gone to a dead sim: the side agents survive (they are
        script-side Agents), only the engine tables are empty. One re-declare has to bring
        all of it back -- relations, self-ally, icon colours and diplomacy colours.
        """
        declare_sides([1, 2])
        self.sim.side_relations.clear()
        self.sim.side_icon_colors.clear()
        self.sim.diplomacy_colors.clear()

        declare_sides([1, 2])

        self.assertEqual(_rel(self.sim, "enemy", "friendly"), sbs.DIPLOMACY.HOSTILE)
        self.assertEqual(_rel(self.sim, "enemy", "enemy"), sbs.DIPLOMACY.ALLIED)
        self.assertEqual(_rel(self.sim, "friendly", "friendly"), sbs.DIPLOMACY.ALLIED)
        self.assertEqual(self.sim.side_icon_colors["enemy"], "#F00")
        self.assertEqual(self.sim.diplomacy_colors[int(sbs.DIPLOMACY.HOSTILE)], "#F00")

    def test_set_diplomacy_colors_reports_no_sim(self):
        from sbs_utils.helpers import FrameContext
        FrameContext.context.sim = None
        self.assertFalse(set_diplomacy_colors())


class A2xStaleSimTests(unittest.TestCase):
    """The frame hazard itself, in the shape the engine has it.

    The base mock re-__init__s its simulation in place, so a stale FrameContext handle can
    never be observed there -- which is exactly why the headless runner could not reproduce
    this bug. Model it directly: a sim swapped out from under a context that still holds
    the old object.
    """

    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_writes_after_a_sim_swap_land_on_the_orphan(self):
        from sbs_utils.helpers import FrameContext
        orphan = FrameContext.context.sim

        # What sim_create() does in the engine, from the caller's point of view: the module
        # global moves on, the context handle does not.
        new_sim = sbs.simulation()
        sbs.sim = new_sim
        self.assertIsNot(FrameContext.context.sim, new_sim)

        declare_sides([1, 2])
        self.assertEqual(orphan.diplomacy_colors[int(sbs.DIPLOMACY.HOSTILE)], "#F00")
        self.assertEqual(new_sim.diplomacy_colors, {},
                         "writes should have gone to the stale handle -- if this fails the "
                         "hazard model is wrong, not the code")

        # ...and re-declaring on a fresh context (the next engine event) repairs it fully.
        FrameContext.context.sim = new_sim
        declare_sides([1, 2])
        self.assertEqual(new_sim.diplomacy_colors[int(sbs.DIPLOMACY.HOSTILE)], "#F00")
        self.assertEqual(_rel(new_sim, "enemy", "friendly"), sbs.DIPLOMACY.HOSTILE)
        self.assertEqual(_rel(new_sim, "enemy", "enemy"), sbs.DIPLOMACY.ALLIED)


if __name__ == "__main__":
    unittest.main()
