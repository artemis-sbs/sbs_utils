"""Declaring sides must stay REPAIRING, not just harmless.

This is the counterweight to the `once` modifier: `create_sides` must NEVER be
one-shot. `sim_create()` leaves `FrameContext.context.sim` stale for the rest of the
frame, so side writes issued in that frame land on a discarded simulation - silently,
because the scripting link graph survives and every check still passes while the
engine's tables stay at their defaults and contacts render grey. The only cure is
re-declaring later, which is exactly what a2x's re-assert loop does.

So a re-declare has to be a full re-issue, not an early-out. These tests pin that, plus
the two silent bugs found alongside (side_set_display_name wrote to the unresolved key,
side_is_color_used compared against the wrong argument).
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.sides import (
    side_ensure, side_create, side_keys_set, side_are_enemies, side_are_allies,
    side_set_relations, side_get_display_name, side_set_display_name,
    side_is_color_used, side_get_side_color, to_side_id,
)
from sbs_utils.procedural.a2x.sides import declare_sides


class SideDeclarationIdempotentTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_side_ensure_returns_the_same_agent(self):
        first = side_ensure("kralien")
        second = side_ensure("kralien")
        self.assertEqual(second, first)
        self.assertEqual(len(side_keys_set()), 1)

    def test_side_create_reconfigures_in_place(self):
        first = side_create("tsn", name="TSN")
        again = side_create("tsn", name="TSN Fleet")
        self.assertEqual(again, first, "re-create must not mint a second side agent")
        self.assertEqual(len(side_keys_set()), 1)
        self.assertEqual(side_get_display_name("tsn"), "TSN Fleet")

    def test_a2x_declare_sides_is_repeatable_and_repairing(self):
        declare_sides([1, 2])
        keys = set(side_keys_set())
        self.assertTrue(side_are_enemies("enemy", "friendly"))
        # A second declare is the REPAIR path (post sim_create). It must not early-out,
        # must not duplicate sides, and must leave relations intact.
        declare_sides([1, 2])
        self.assertEqual(set(side_keys_set()), keys)
        self.assertTrue(side_are_enemies("enemy", "friendly"))
        self.assertTrue(side_are_allies("friendly", "friendly"))

    def test_redeclare_reissues_engine_relationship_writes(self):
        # The silent failure this guards: the link graph survives a stale sim while the
        # ENGINE table does not, so a re-declare has to write the engine side again.
        declare_sides([1, 2])
        calls = []
        original = self.sim.set_side_relationship
        self.sim.set_side_relationship = lambda *a, **k: calls.append(a)
        try:
            declare_sides([1, 2])
        finally:
            self.sim.set_side_relationship = original
        self.assertTrue(calls, "re-declare must re-issue the engine relationship writes")


class SideSetterBugTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_display_name_by_key_actually_applies(self):
        side_create("tsn", name="TSN")
        side_set_display_name("tsn", "TSN Fleet")
        self.assertEqual(side_get_display_name("tsn"), "TSN Fleet")

    def test_display_name_by_id_still_applies(self):
        sid = side_create("tsn", name="TSN")
        side_set_display_name(sid, "Renamed")
        self.assertEqual(side_get_display_name("tsn"), "Renamed")

    def test_is_color_used_compares_the_color(self):
        side_create("tsn", name="TSN", color="#00F")
        self.assertTrue(side_is_color_used("#00F"))
        self.assertFalse(side_is_color_used("#F0F"),
                         "an unused color must not report as used")


if __name__ == "__main__":
    unittest.main()
