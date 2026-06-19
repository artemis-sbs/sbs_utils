"""Tests for sbs_utils.helpers utility functions."""
import unittest
from sbs_utils.helpers import split_props


class TestSplitProps(unittest.TestCase):
    """split_props(s, def_key) — parses Cosmos style strings."""

    # ── normal style strings ──────────────────────────────────────────────────

    def test_single_key_value(self):
        self.assertEqual(split_props("color:red;", "text"), {"color": "red"})

    def test_multiple_key_values(self):
        self.assertEqual(
            split_props("color:red;font-size:2em;", "text"),
            {"color": "red", "font-size": "2em"},
        )

    def test_no_trailing_semicolon(self):
        self.assertEqual(
            split_props("color:red;font-size:2em", "text"),
            {"color": "red", "font-size": "2em"},
        )

    def test_empty_string(self):
        self.assertEqual(split_props("", "text"), {})

    # ── default-key fallback ─────────────────────────────────────────────────

    def test_no_colon_uses_def_key(self):
        self.assertEqual(split_props("plain text", "$text"), {"$text": "plain text"})

    # ── colon inside plain text content ──────────────────────────────────────
    # Bug fixed: text like "Hello, World! Clicks: 0" was split on the colon
    # inside the sentence, producing key "Hello, World! Clicks" (with spaces)
    # instead of falling back to def_key. The fix detects whitespace in the
    # candidate key and treats the whole string as the def_key value.
    #
    # Note: single-word strings like "Clicks: 0" are ambiguous — "Clicks" looks
    # like a valid style key and is still parsed as one. The fix targets the
    # common case of sentence-like text that contains spaces before the colon.

    def test_sentence_with_colon_uses_def_key(self):
        result = split_props("Hello, World! Clicks: 42", "$text")
        self.assertEqual(result, {"$text": "Hello, World! Clicks: 42"})

    def test_multi_word_key_with_colon_uses_def_key(self):
        result = split_props("Mission status: active", "$text")
        self.assertEqual(result, {"$text": "Mission status: active"})

    def test_single_word_before_colon_is_treated_as_key(self):
        # "Clicks" has no whitespace so it is parsed as a style key — this is
        # the known limitation of the whitespace-based heuristic.
        result = split_props("Clicks: 0", "$text")
        self.assertEqual(result, {"Clicks": " 0"})

    # ── $text key mixed with other style keys ─────────────────────────────────

    def test_text_key_before_other_keys(self):
        result = split_props("$text:Clicks: 0;color:red;", "def")
        # $text: is a valid identifier-like key (no whitespace) so it parses normally
        self.assertEqual(result["$text"], "Clicks: 0")
        self.assertEqual(result["color"], "red")

    def test_area_style_string(self):
        result = split_props("area:10,20,90,80;", "def")
        self.assertEqual(result, {"area": "10,20,90,80"})

    def test_font_size_with_unit(self):
        result = split_props("font-size:2em;color:#7cf;", "def")
        self.assertEqual(result, {"font-size": "2em", "color": "#7cf"})


if __name__ == "__main__":
    unittest.main()
