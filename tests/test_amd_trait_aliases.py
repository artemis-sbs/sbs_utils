"""A trait's `aka` spellings never resolved, and its fields never reached the game.

_alias_index merged GLOBAL and the archetype table and nothing else, and
_declared_under looked in the same two - so a trait could declare `aka` and no
author spelling ever landed on it. Worse, the RUNTIME never knew a record had
traits at all: amd_parse_facts called amd_is_declared/amd_read_field without them,
so a trait's fields were declared for the LINTER and undeclared for the GAME. The
reader fell through to amd_num, and a trait field the schema called an enum came
back as whatever amd_num made of it.

This matters for the OpenUniverse build-out rather than for today: the two core
traits (economy, reputation) declare no `aka`, which is exactly why nobody noticed.

The compatibility rule this file pins: TRAIT ALIASES ARE CONSULTED LAST. Anything
that resolves today must keep resolving to the same field, so a trait can only fill
in a name nothing else claims.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_schema as S
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.amd_lint import amd_lint

NL = chr(10)


class TraitBase(unittest.TestCase):
    def setUp(self):
        self.snap = S.amd_vocabulary_snapshot()
        S.amd_register_trait("haulage", {
            "cargo rating": S.field(S.text(), aka=("tonnage", "hold size")),
        }, domain="test")

    def tearDown(self):
        S.amd_vocabulary_restore(self.snap)


class TestTraitFieldsReachTheGame(TraitBase):
    def _parse(self, body):
        return amd_parse_facts(NL.join(body) + NL, archetype="quest")

    def test_a_trait_field_is_declared_once_the_record_claims_it(self):
        self.assertFalse(S.amd_is_declared("cargo rating", "quest"))
        self.assertTrue(S.amd_is_declared("cargo rating", "quest", ("haulage",)))

    def test_the_runtime_reads_it_through_the_records_own_Also(self):
        # The whole point: the record says `Also: haulage`, and the parser must pick
        # that up itself - no caller passes traits in.
        data = self._parse(["Also: haulage", "Cargo rating: heavy"])
        self.assertEqual(data.get("cargo_rating"), "heavy")

    def test_an_alias_resolves_to_the_trait_field(self):
        data = self._parse(["Also: haulage", "Tonnage: heavy"])
        self.assertEqual(data.get("cargo_rating"), "heavy",
                         "a trait's aka spelling did not land on its field")

    def test_a_spaced_alias_normalizes_like_any_other(self):
        data = self._parse(["Also: haulage", "Hold Size: heavy"])
        self.assertEqual(data.get("cargo_rating"), "heavy")

    def test_without_the_claim_it_stays_undeclared(self):
        data = self._parse(["Tonnage: heavy"])
        self.assertNotIn("cargo_rating", data)
        self.assertIn("tonnage", data)

    def test_an_implicit_archetype_trait_needs_no_Also(self):
        S.amd_register_archetype_traits("quest", ("haulage",))
        self.assertTrue(S.amd_is_declared("cargo rating", "quest"))
        data = self._parse(["Tonnage: heavy"])
        self.assertEqual(data.get("cargo_rating"), "heavy")


class TestTheLinterAgrees(TraitBase):
    def _codes(self, body):
        src = "# [R](r)" + NL + "---" + NL + NL.join(body) + NL + "---" + NL
        return [f.code for f in amd_lint(content=src, cross_file=False)]

    def test_a_trait_field_is_not_unknown_when_claimed(self):
        codes = self._codes(["Job", "Also: haulage", "Cargo rating: heavy",
                             "Reward: 1 credits"])
        self.assertNotIn("unknown-field", codes)

    def test_its_alias_is_not_unknown_either(self):
        codes = self._codes(["Job", "Also: haulage", "Tonnage: heavy",
                             "Reward: 1 credits"])
        self.assertNotIn("unknown-field", codes)

    def test_it_is_still_unknown_without_the_claim(self):
        codes = self._codes(["Job", "Tonnage: heavy", "Reward: 1 credits"])
        self.assertIn("unknown-field", codes)


class TestCompatibilityRule(unittest.TestCase):
    """Trait aliases are consulted LAST, so they can only fill in an unclaimed name."""

    def setUp(self):
        self.snap = S.amd_vocabulary_snapshot()

    def tearDown(self):
        S.amd_vocabulary_restore(self.snap)

    def test_an_archetype_field_of_the_same_name_still_wins(self):
        S.amd_register_trait("greedy", {"greedy reward": S.field(S.text(), aka=("reward",))},
                             domain="test")
        # `Reward:` is a real quest field; a trait may not steal it.
        self.assertEqual(S.amd_canonical_label("reward", "quest", ("greedy",)), "reward")
        data = amd_parse_facts("Also: greedy" + NL + "Reward: 250 credits" + NL,
                               archetype="quest")
        self.assertIn("reward", data)
        self.assertNotIn("greedy_reward", data)

    def test_a_global_field_of_the_same_name_still_wins(self):
        S.amd_register_trait("shouty", {"shouty color": S.field(S.text(), aka=("color",))},
                             domain="test")
        self.assertEqual(S.amd_canonical_label("color", "quest", ("shouty",)), "color")

    def test_registering_a_trait_invalidates_the_alias_cache(self):
        # The other half of the same bug: amd_register_trait never cleared it, so a
        # trait registered after any lookup stayed invisible for the whole run.
        self.assertEqual(S.amd_canonical_label("late_alias", "quest", ("late",)),
                         "late_alias")
        S.amd_register_trait("late", {"late field": S.field(S.text(), aka=("late_alias",))},
                             domain="test")
        self.assertEqual(S.amd_canonical_label("late_alias", "quest", ("late",)),
                         "late_field")

    def test_traits_do_not_leak_between_archetypes(self):
        S.amd_register_trait("only_here", {"only field": S.text()}, domain="test")
        self.assertTrue(S.amd_is_declared("only field", "quest", ("only_here",)))
        self.assertFalse(S.amd_is_declared("only field", "quest"))
        self.assertFalse(S.amd_is_declared("only field", "lifeform"))


if __name__ == "__main__":
    unittest.main()
