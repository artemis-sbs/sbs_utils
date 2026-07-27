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
    def test_flow_is_per_value_not_per_fence(self):
        # A flow VALUE is parsed as flow...
        self.assertEqual(amd_parse_facts("Modifiers: {speed: 2}"),
                         {"modifiers": {"speed": 2}})
        # ...and it no longer drags the rest of the fence into YAML with it. Both of
        # these used to break: '#86c' would be eaten as a comment, and the colon in
        # the Reveals value would raise.
        self.assertEqual(
            amd_parse_facts("Modifiers: {speed: 2}\nColor: #86c\n"
                            "Reveals: Survey logged: 3 crates"),
            {"modifiers": {"speed": 2}, "color": "#86c",
             "reveals": "Survey logged: 3 crates"})

    def test_brace_mid_value_stays_text(self):
        self.assertEqual(amd_parse_facts("Intel: Captain {name}\nColor: #07F"),
                         {"intel": "Captain {name}", "color": "#07F"})

    def test_fact_lines_skips_noise(self):
        text = "Color: red\n// a comment\n\nno colon here\nSize: 3"
        self.assertEqual(list(amd_fact_lines(text)),
                         [("color", "red"), ("size", "3")])

    def test_default_coercion(self):
        # no handler -> amd_norm(label) key, amd_num(value)
        self.assertEqual(amd_parse_facts("Loot Max: 7\nName: scout"),
                         {"loot_max": 7, "name": "scout"})

    # --- the grammar the redesign added -------------------------------------
    def test_kind_line_is_the_bare_first_noun(self):
        from sbs_utils.procedural.amd import KIND_KEY, amd_kind_line
        d = amd_parse_facts("Characters\nColor: #07F")
        self.assertEqual(d[KIND_KEY], "characters")
        self.assertEqual(d["color"], "#07F")
        # blanks and // comments may precede it
        self.assertEqual(amd_kind_line("\n// who these are\nCharacters\nColor: #07F"),
                         "Characters")
        # a fence with no kind line is unaffected
        self.assertNotIn(KIND_KEY, amd_parse_facts("Color: #07F"))

    def test_kind_line_anywhere_else_is_reported(self):
        errs = []
        amd_parse_facts("Color: #07F\nCharacters", errors=errs)
        self.assertEqual(len(errs), 1)
        self.assertIn("first line", errs[0])

    def test_empty_value_plus_indent_nests(self):
        d = amd_parse_facts("Properties:\n  Monster: shark\n  Mode: attract")
        self.assertEqual(d["properties"], {"Monster": "shark", "Mode": "attract"})

    def test_empty_value_plus_dashes_is_a_list(self):
        d = amd_parse_facts('Lines:\n  - "First bark."\n  - "Second bark."')
        self.assertEqual(d["lines"], ["First bark.", "Second bark."])

    def test_inline_value_plus_indent_continues_it(self):
        # the 515-character Citation in stormsbeacon.amd finally wraps
        d = amd_parse_facts("Citation: At the origin, with the guns lighting\n"
                            "  the dark, she seated the last piece.")
        self.assertEqual(d["citation"],
                         "At the origin, with the guns lighting the dark, "
                         "she seated the last piece.")

    def test_nesting_and_continuation_are_told_apart_by_the_value(self):
        d = amd_parse_facts("Wraps: one\n  two\nNests:\n  Inner: 3")
        self.assertEqual(d["wraps"], "one two")
        self.assertEqual(d["nests"], {"Inner": 3})

    def test_a_colonless_line_is_an_error_not_a_silent_drop(self):
        errs = []
        d = amd_parse_facts("Color: #07F\nSize: 3\n  stray words", errors=errs)
        # (indented under Size, so it continues it - the ERROR case is unindented)
        self.assertEqual(d["size"], "3 stray words")
        errs = []
        amd_parse_facts("Colour red\nSize: 3", errors=errs)
        self.assertTrue(errs and "Label: value" in errs[0])

    def test_errors_never_raise(self):
        # a mission must not die on a typo; the linter is what makes it loud
        d = amd_parse_facts("Color: #07F\n}}} broken {{{\nSize: 3")
        self.assertEqual(d["color"], "#07F")
        self.assertEqual(d["size"], 3)

    def test_handler_consumes_and_falls_through(self):
        def handler(data, label, value):
            if label == "color":
                data["colour"] = value        # remap
                return True
            return None                        # everything else -> default
        out = amd_parse_facts("Color: red\nSpeed: 5", handler)
        self.assertEqual(out, {"colour": "red", "speed": 5})

    def test_is_yaml_flow(self):
        # PER-VALUE now, not per-fence: a value that OPENS with a bracket is flow.
        # It used to scan the whole block, so one prose value carrying a brace
        # (`Intel: Captain {name}`) silently reparsed every other line as YAML -
        # where `Color: #07F` becomes None and a colon in a value raises.
        self.assertTrue(amd_is_yaml_flow("[1, 2]"))
        self.assertTrue(amd_is_yaml_flow("{a: 1}"))
        self.assertTrue(amd_is_yaml_flow("  {a: 1}"))    # leading space is fine
        self.assertFalse(amd_is_yaml_flow("1"))
        self.assertFalse(amd_is_yaml_flow("Captain {name}"))   # brace mid-value: text


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
