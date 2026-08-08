"""`Drops:` - what a kill leaves behind, authored per role (PRM-14, PRM-35).

Condemned hulks on a live-fire range dropped contraband, because they are spawned hostile
so Weapons can lock them and the library's default drop is a random trade good. Loot
should follow from what a ship IS, and an author should be able to see and change it
without reading MAST.

The distinction these tests exist to protect: **no table** and an **empty table** are not
the same thing. No table means "do whatever you did before"; `Drops: none` means "this one
drops nothing". Collapse them and `Drops: none` silently becomes a no-op - which is the
one thing the feature was asked for.

    python -m unittest tests.test_amd_drops
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural import amd_drops as D


class ParseTests(unittest.TestCase):
    def test_none_is_an_empty_table_not_a_missing_one(self):
        self.assertEqual([], D.drop_table_parse("none"))

    def test_a_bare_key_is_one_of_it(self):
        self.assertEqual([{"key": "contraband", "low": 1, "high": 1, "chance": 1.0}],
                         D.drop_table_parse("contraband"))

    def test_a_count(self):
        self.assertEqual(3, D.drop_table_parse("salvage x3")[0]["low"])

    def test_a_range(self):
        e = D.drop_table_parse("salvage x2-4")[0]
        self.assertEqual((2, 4), (e["low"], e["high"]))

    def test_a_chance(self):
        self.assertAlmostEqual(0.2, D.drop_table_parse("contraband 20%")[0]["chance"])

    def test_a_range_and_a_chance_together(self):
        e = D.drop_table_parse("salvage x2-4 50%")[0]
        self.assertEqual((2, 4), (e["low"], e["high"]))
        self.assertAlmostEqual(0.5, e["chance"])

    def test_a_backwards_range_is_read_the_right_way_round(self):
        e = D.drop_table_parse("salvage x4-2")[0]
        self.assertEqual((2, 4), (e["low"], e["high"]))

    def test_junk_does_not_raise(self):
        self.assertEqual([], D.drop_table_parse(""))
        self.assertEqual([], D.drop_table_parse(None))


class LookupTests(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        D.drops_clear()
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))
        add_role(self.ship, "raider")

    def tearDown(self):
        D.drops_clear()

    def test_no_table_at_all_returns_None(self):
        """Which is the signal to the caller: keep doing what you did before."""
        self.assertIsNone(D.drops_table_for(self.ship))

    def test_an_empty_table_is_NOT_None(self):
        D.drops_register("raider", "none")
        self.assertEqual([], D.drops_table_for(self.ship))
        self.assertEqual([], D.drops_roll(self.ship))

    def test_the_first_authored_role_wins(self):
        """Author order decides, so a specific role written first beats a general one."""
        add_role(self.ship, "target_drone")
        D.drops_register("target_drone", "none")
        D.drops_register("raider", "salvage x9")
        self.assertEqual([], D.drops_table_for(self.ship))

    def test_a_role_the_object_lacks_is_ignored(self):
        D.drops_register("civilian", "salvage x9")
        self.assertIsNone(D.drops_table_for(self.ship))

    def test_a_certain_drop_always_rolls(self):
        D.drops_register("raider", "salvage x2")
        self.assertEqual([("salvage", 2)], D.drops_roll(self.ship))

    def test_an_impossible_chance_never_rolls(self):
        D.drops_register("raider", "contraband 0%")
        self.assertEqual([], D.drops_roll(self.ship))

    def test_re_registering_a_role_replaces_it(self):
        D.drops_register("raider", "salvage x2")
        D.drops_register("raider", "none")
        self.assertEqual([], D.drops_table_for(self.ship))

    def test_the_reset_forgets_every_table(self):
        D.drops_register("raider", "salvage x2")
        D.drops_clear()
        self.assertIsNone(D.drops_table_for(self.ship))
        self.assertEqual(0, D.drops_size())

    def test_spawning_produces_one_pickup_per_entry(self):
        """A cache carrying n, not n objects to fly through."""
        D.drops_register("raider", "salvage x3, contraband 100%")
        self.assertEqual(2, D.drops_spawn(self.ship))


if __name__ == "__main__":
    unittest.main()


class OneGrammarTests(unittest.TestCase):
    """The runtime reads the table; the parser turns its keys into references and the
    linter checks them. Two parsers would mean the linter blessing loot the game then
    ignores, so there is one - `amd.amd_drop_table` - and this pins them together."""

    SAMPLES = ("salvage", "salvage x2-4, contraband 20%", "a x1 50%, b, c x3",
               "none", "", "   ", "junk x, x2 lonely")

    def test_the_runtime_parser_is_the_shared_one(self):
        from sbs_utils.procedural.amd import amd_drop_table
        for s in self.SAMPLES:
            self.assertEqual(D.drop_table_parse(s), amd_drop_table(s), s)

    def test_the_keys_the_linter_sees_are_the_keys_the_game_drops(self):
        from sbs_utils.procedural.amd import amd_drop_keys
        for s in self.SAMPLES:
            self.assertEqual(amd_drop_keys(s), [e["key"] for e in D.drop_table_parse(s)], s)

    def test_an_already_parsed_table_survives_a_second_parse(self):
        """The reader and the linter may both reach the same value; parsing twice must
        not turn a table into the string `[{'key': ...}]`."""
        once = D.drop_table_parse("salvage x2-4, contraband 20%")
        self.assertEqual(D.drop_table_parse(once), once)
