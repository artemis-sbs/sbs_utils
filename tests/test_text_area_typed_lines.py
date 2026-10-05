"""A sentence is not a list item because of how it starts.

Found by the lesson "Markdown in twenty minutes" and seen in the real engine, 2026-10-04:
the text area took ANY line that began with a digit for a numbered item and ANY line that
began with a hyphen for a bullet, and threw the first word away with the marker.

    40 years ago she was the pride of the fleet.   ->   1. years ago she was the pride ...
    -Find her.                                     ->   - her.
    $500 says she is not empty.                    ->   says she is not empty.

The end-to-end twin, through the shipped Quest Log, is LegendaryMissions'
documents/test_quest_log_pane.py.

    python -m unittest tests.test_text_area_typed_lines
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.pages.layout.text_area import TextArea


class WhatStartsAList(unittest.TestCase):
    def setUp(self):
        self.area = TextArea("t", "x", markdown=True)
        self.plain = self.area.get_style("_")

    def read(self, line):
        """(style key or 'carried', the text kept)."""
        key, text = self.area.get_line_style(line, self.plain)
        return ("carried" if key is self.plain else key), text

    def test_a_sentence_that_starts_with_a_number(self):
        for line in ("40 years ago she was the pride of the fleet.", "2187 was a bad year.",
                     "0800 hours.", "3"):
            with self.subTest(line=line):
                self.assertEqual(self.read(line), ("carried", line))

    def test_a_numbered_item_is_digits_a_stop_or_a_bracket_and_a_space(self):
        self.assertEqual(self.read("1. Find her."), ("ol", "Find her."))
        self.assertEqual(self.read("12) Scan her."), ("ol", "Scan her."))

    def test_a_bullet_is_a_hyphen_and_a_space(self):
        self.assertEqual(self.read("- Find her."), ("ul", "Find her."))
        for line in ("-Find her.", "---", "-40 degrees outside."):
            with self.subTest(line=line):
                self.assertEqual(self.read(line), ("carried", line))

    def test_a_dollar_sign_names_a_style_only_when_there_is_one(self):
        self.assertEqual(self.read("$500 says she is not empty."),
                         ("carried", "$500 says she is not empty."))
        key, text = self.area.get_line_style("$p1 A quieter line.", self.plain)
        self.assertEqual((key, text.strip()), ("p1", "A quieter line."))

    def test_a_heading_is_unchanged(self):
        self.assertEqual(self.read("# Orders")[0], "h1")


if __name__ == "__main__":
    unittest.main()
