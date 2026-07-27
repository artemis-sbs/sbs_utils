"""Friendly AMD fact-fence reader (sbs_utils.procedural.amd) - the generic
parsing + coercion extracted from the Open Universe. Pure; no engine/sim."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import unittest
from sbs_utils.procedural.amd import (
    amd_norm, amd_num, amd_pct, amd_list, amd_weighted, amd_makeup,
    amd_coords, amd_is_yaml_flow, amd_fact_lines, amd_parse_facts)


class TestAmdPrimitives(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(amd_norm("By-The Book"), "by_the_book")

    def test_num(self):
        self.assertEqual(amd_num("5"), 5)
        self.assertEqual(amd_num("1.5"), 1.5)
        self.assertEqual(amd_num("hi"), "hi")

    def test_pct(self):
        self.assertEqual(amd_pct("40%"), 0.4)
        self.assertEqual(amd_pct("0.4"), 0.4)
        self.assertEqual(amd_pct("x"), "x")

    def test_list(self):
        self.assertEqual(amd_list("a, b ,, c"), ["a", "b", "c"])

    def test_weighted(self):
        self.assertEqual(amd_weighted("by-the-book 40, fearsome 30"),
                         {"by_the_book": 40, "fearsome": 30})
        self.assertEqual(amd_weighted("lone")["lone"], 0)

    def test_makeup(self):
        self.assertEqual(amd_makeup("60% Kralien, 40% Arvonian"),
                         {"Kralien": 60, "Arvonian": 40})
        self.assertEqual(amd_makeup("Kralien, Torgoth"), ["Kralien", "Torgoth"])
        self.assertEqual(amd_makeup("Torgoth"), "Torgoth")

    def test_coords(self):
        self.assertEqual(amd_coords("6, 4"), [6, 4])
        self.assertEqual(amd_coords("6 4 9"), [6, 4])   # first n=2


class TestAmdParse(unittest.TestCase):
    def test_yaml_flow_delegates(self):
        # a block with { or [ is parsed as YAML, not fact lines
        self.assertEqual(amd_parse_facts("{a: 1, b: two}"), {"a": 1, "b": "two"})

    def test_fact_lines_skips_noise(self):
        text = "Color: red\n// a comment\n\nno colon here\nSize: 3"
        self.assertEqual(list(amd_fact_lines(text)),
                         [("color", "red"), ("size", "3")])

    def test_default_coercion(self):
        # no handler -> amd_norm(label) key, amd_num(value)
        self.assertEqual(amd_parse_facts("Loot Max: 7\nName: scout"),
                         {"loot_max": 7, "name": "scout"})

    def test_handler_consumes_and_falls_through(self):
        def handler(data, label, value):
            if label == "color":
                data["colour"] = value        # remap
                return True
            return None                        # everything else -> default
        out = amd_parse_facts("Color: red\nSpeed: 5", handler)
        self.assertEqual(out, {"colour": "red", "speed": 5})

    def test_is_yaml_flow(self):
        self.assertTrue(amd_is_yaml_flow("a: [1,2]"))
        self.assertFalse(amd_is_yaml_flow("a: 1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestSharedVocabulary(unittest.TestCase):
    """The primitives the engine's quest parser and the editor's analysis BOTH read.
    They live here so the two can't drift - a view that disagreed with the driver
    about a signal name or a deadline would be silently wrong."""

    def test_signal_name_matches_what_the_driver_matches(self):
        from sbs_utils.procedural.amd import amd_signal_name
        from sbs_utils.procedural.amd_quest import _signal_name
        for raw in ("Eliminated Foe", "  drone_down ", "Barge Delivered"):
            self.assertEqual(amd_signal_name(raw), _signal_name(raw))
        self.assertEqual(amd_signal_name("Eliminated Foe"), "eliminated_foe")

    def test_duration_keeps_the_authored_unit(self):
        from sbs_utils.procedural.amd import amd_duration_parts, amd_duration_seconds
        self.assertEqual(amd_duration_parts("6 minutes"), (6, "minutes"))
        self.assertEqual(amd_duration_parts("90 seconds"), (90, "seconds"))
        self.assertEqual(amd_duration_parts("2"), (2, "minutes"))   # bare = minutes
        self.assertEqual(amd_duration_seconds("6 minutes"), 360)
        self.assertIsNone(amd_duration_seconds("soon"))

    def test_quest_data_still_carries_the_authored_unit(self):
        """The driver sums seconds+minutes, but the stored shape is what was written."""
        from sbs_utils.procedural.amd_quest import amd_quest_data
        self.assertEqual(amd_quest_data("Fail after: 6 minutes")["fail_after"],
                         {"minutes": 6})
        self.assertEqual(amd_quest_data("Complete after: 30 seconds")["complete_after"],
                         {"seconds": 30})
