"""Tests for sbs_utils.helpers utility functions."""
import unittest
from sbs_utils.helpers import split_props, merge_props, gui_text_escape


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

    def test_single_word_capitalized_before_colon_is_text(self):
        # A capitalized word before a colon is NOT a style key (all real keys
        # are lowercase or "$"-prefixed), so it falls back to the default key.
        self.assertEqual(split_props("Clicks: 0", "$text"), {"$text": "Clicks: 0"})
        self.assertEqual(split_props("Upgrades:", "$text"), {"$text": "Upgrades:"})
        self.assertEqual(split_props("Score:5", "$text"), {"$text": "Score:5"})
        self.assertEqual(split_props("HP: 100/100", "$text"), {"$text": "HP: 100/100"})

    def test_lowercase_leading_text_is_still_ambiguous(self):
        # Documented residual gap: all-lowercase text before a colon still
        # reads as a style key. Use a "$text:" prefix to force text.
        self.assertEqual(split_props("ready: go", "$text"), {"ready": " go"})
        self.assertEqual(split_props("$text:ready: go", "$text"), {"$text": "ready: go"})

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

    # ── backtick-quoted values are opaque (issue #569) ────────────────────────

    def test_backtick_value_keeps_inner_semicolon(self):
        # ';' and ':' inside the backticks are literal, not delimiters; the
        # author's trailing style stays a separate property.
        result = split_props("$text:`Bob;font:g`;justify:left;", "$text")
        self.assertEqual(result["$text"], "`Bob;font:g`")
        self.assertEqual(result["justify"], "left")

    def test_backtick_value_with_leading_space(self):
        result = split_props("$text: `a:b;c`;color:red;", "$text")
        self.assertEqual(result["$text"], " `a:b;c`")
        self.assertEqual(result["color"], "red")

    def test_backtick_roundtrips_through_merge(self):
        s = "$text:`Bob;font:g`;justify:left;"
        self.assertEqual(merge_props(split_props(s, "$text")), s)

    def test_unquoted_values_unchanged(self):
        # No backtick -> identical to legacy behavior (back-compat).
        self.assertEqual(split_props("$text:Artemis;justify:left;", "$text"),
                         {"$text": "Artemis", "justify": "left"})


class TestGuiTextEscape(unittest.TestCase):
    """gui_text_escape(s) — wrap a dynamic value for safe $text: inclusion."""

    def test_none_and_empty_return_empty(self):
        self.assertEqual(gui_text_escape(None), "")
        self.assertEqual(gui_text_escape(""), "")

    def test_plain_value_is_wrapped(self):
        self.assertEqual(gui_text_escape("Bob"), "`Bob`")

    def test_injection_chars_are_wrapped_not_stripped(self):
        self.assertEqual(gui_text_escape("abc;font:g"), "`abc;font:g`")

    def test_literal_backtick_is_stripped(self):
        self.assertEqual(gui_text_escape("a`b"), "`ab`")

    def test_non_string_is_coerced(self):
        self.assertEqual(gui_text_escape(42), "`42`")


if __name__ == "__main__":
    unittest.main()
