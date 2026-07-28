"""Traits: a concern a record ALSO has, on top of what it is
(sbs_utils.procedural.amd_schema).

    python -m unittest tests.test_amd_traits
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_schema as S


class AnArchetypeCanAlwaysHaveOne(unittest.TestCase):
    """`Also:` is for OPTIONAL concerns. A side is always regarded some way and so is a
    person, so writing `Also: reputation` on every one of them would be ceremony - the
    archetype carries it, and the trait stays the single declaration."""

    def test_a_side_is_regarded_without_saying_so(self):
        self.assertEqual(S.field_schema("values", "side")["type"], "weighted")
        self.assertEqual(S.field_schema("reliability", "lifeform")["type"], "pct")

    def test_an_archetype_that_does_NOT_carry_it_is_unaffected(self):
        self.assertEqual(S.field_schema("reliability", "quest")["type"], "text")

    def test_a_mission_can_add_one(self):
        S.amd_register_trait("weather", {"forecast": S.text()})
        S.amd_register_archetype_traits("region", ("weather",), domain="test")
        self.assertTrue(S.amd_is_declared("forecast", "region"))
        self.assertFalse(S.amd_is_declared("forecast", "item"))

    def test_registering_the_same_trait_twice_is_a_no_op(self):
        before = tuple(S.ARCHETYPE_TRAITS.get("side", ()))
        S.amd_register_archetype_traits("side", ("reputation",))
        self.assertEqual(tuple(S.ARCHETYPE_TRAITS.get("side", ())), before)


class TraitsLendTheirWords(unittest.TestCase):
    """A worldlet is a Landmark that yields ore. Inventing an archetype for the second
    half is what produced `worldlet`, `clan` and `captain` as private types."""

    def test_a_trait_types_a_field_the_archetype_never_heard_of(self):
        self.assertEqual(S.field_schema("price", "landmark")["type"], "text")
        self.assertEqual(S.field_schema("price", "landmark", ("economy",))["type"], "int")

    def test_the_ARCHETYPE_wins_a_collision(self):
        """What a record IS beats what it also does - `Price:` on an item means the
        item's price, whatever a trait would say."""
        item_own = S.field_schema("price", "item")
        self.assertEqual(S.field_schema("price", "item", ("economy",)), item_own)

    def test_traits_apply_in_the_order_written(self):
        S.amd_register_trait("first_wins", {"shared_label": S.integer()})
        S.amd_register_trait("second", {"shared_label": S.color()})
        self.assertEqual(
            S.field_schema("shared label", None, ("first_wins", "second"))["type"], "int")
        self.assertEqual(
            S.field_schema("shared label", None, ("second", "first_wins"))["type"], "color")

    def test_an_unknown_trait_is_harmless(self):
        self.assertEqual(S.field_schema("price", "landmark", ("nonsense",))["type"], "text")

    def test_Also_is_declared_everywhere(self):
        # so the field itself is never flagged as unknown, on any archetype
        self.assertTrue(S.amd_is_declared("also", "landmark"))
        self.assertTrue(S.amd_is_declared("also", "quest"))

    def test_reading_the_claim_off_a_record(self):
        self.assertEqual(S.amd_traits_of({"also": "economy"}), ("economy",))
        self.assertEqual(S.amd_traits_of({"also": "economy, reputation"}),
                         ("economy", "reputation"))
        self.assertEqual(S.amd_traits_of({}), ())
        self.assertEqual(S.amd_traits_of(None), ())

    def test_a_trait_can_be_extended_by_a_mission(self):
        S.amd_register_trait("economy", {"upkeep": S.integer()}, domain="test")
        self.assertEqual(S.field_schema("upkeep", "landmark", ("economy",))["type"], "int")

    def test_redeclaring_a_trait_field_differently_is_LOUD(self):
        with self.assertRaises(ValueError):
            S.amd_register_trait("economy", {"upkeep": S.color()}, domain="test")


if __name__ == "__main__":
    unittest.main()
