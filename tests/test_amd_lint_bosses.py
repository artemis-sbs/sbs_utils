"""Two mistakes a first boss file makes, which linted clean and did nothing.

Both were found by writing the first author lesson - "copy the Warlord and rename it" -
and then doing what a new author does:

  * copy the file and forget to rename the heading. Two files say `# [Warlord](...)`,
    the boss list offers bosses by name, and one of them is simply not there;
  * give the flagship a two-word name. `Named: Iron Duke kralien_dreadnought` is a ship
    called `Iron` on a hull called `Duke`.

    python -m unittest tests.test_amd_lint_bosses
"""
import os
import shutil
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_lint as L
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_schema import (amd_register_fields, named_hulls,
                                             amd_vocabulary_snapshot,
                                             amd_vocabulary_restore, field_schema)

BOSS = """# [{display}]({key})
---
Boss
Trigger: enemies_low
Flagships: {flagships}
---
A boss.
"""


def _codes(findings):
    return [f.code for f in findings]


class NamedHullsTests(unittest.TestCase):
    def setUp(self):
        self._snap = amd_vocabulary_snapshot()
        amd_register_fields("map", {"flagships": named_hulls()}, domain="test_bosses")
        self._real_art = L._relic_known_art
        L._relic_known_art = lambda: {"kralien_dreadnought", "tsn_juggernaut"}

    def tearDown(self):
        L._relic_known_art = self._real_art
        amd_vocabulary_restore(self._snap)

    def _lint(self, flagships):
        return amd_lint(content=BOSS.format(display="Queen", key="queen", flagships=flagships))

    def test_it_is_still_a_comma_list(self):
        """The type must not change, or the field reads differently to every caller."""
        self.assertEqual(field_schema("flagships", "map").get("type"), "csv")

    def test_a_name_and_a_hull_is_clean(self):
        got = self._lint("Morrigan kralien_dreadnought, Ragnarok tsn_juggernaut")
        self.assertNotIn("hull-name-shape", _codes(got))
        self.assertNotIn("unknown-hull", _codes(got))

    def test_a_two_word_name_is_flagged_with_the_fix(self):
        got = [f for f in self._lint("Iron Duke kralien_dreadnought")
               if f.code == "hull-name-shape"]
        self.assertEqual(len(got), 1)
        self.assertIn("`Iron`", got[0].message)
        self.assertIn("`Duke`", got[0].message)
        self.assertIn("Iron_Duke kralien_dreadnought", got[0].message)

    def test_only_the_bad_entry_is_flagged_and_it_is_located(self):
        src = BOSS.format(display="Queen", key="queen",
                          flagships="Morrigan kralien_dreadnought, Iron Duke tsn_juggernaut")
        got = [f for f in amd_lint(content=src) if f.code == "hull-name-shape"]
        self.assertEqual(len(got), 1)
        line = src.splitlines()[got[0].line - 1]
        self.assertEqual(line[got[0].col:got[0].end_col], "Iron Duke tsn_juggernaut")

    def test_a_name_with_no_hull_is_flagged(self):
        self.assertIn("hull-name-shape", _codes(self._lint("Morrigan")))

    def test_an_unknown_hull_is_flagged(self):
        got = [f for f in self._lint("Morrigan kralien_dreadnaught") if f.code == "unknown-hull"]
        self.assertEqual(len(got), 1)
        self.assertIn("kralien_dreadnaught", got[0].message)

    def test_no_catalog_means_no_opinion_on_the_hull(self):
        """`sbs lint` runs where shipData may be unreachable; say nothing, do not guess."""
        L._relic_known_art = lambda: set()
        got = self._lint("Morrigan anything_at_all")
        self.assertNotIn("unknown-hull", _codes(got))

    def test_an_ordinary_comma_list_is_left_alone(self):
        """Only a field DECLARED named_hulls is held to the shape."""
        src = "# [Camp](camp)\n---\nLandmark\nRoles: one two three, four\n---\nA place.\n"
        self.assertNotIn("hull-name-shape", _codes(amd_lint(content=src)))


class DuplicateBossNameTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="amd_boss_lint_")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _write(self, name, display, key, kind="Boss"):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# [{display}]({key})\n---\n{kind}\nTrigger: enemies_low\n---\nA boss.\n")
        return path

    def _dupes(self, path):
        return [f for f in amd_lint(file_path=path) if f.code == "duplicate-boss-name"]

    def test_a_copy_that_was_never_renamed_is_flagged_and_names_the_other_file(self):
        self._write("warlord.amd", "Warlord", "warlord")
        copy = self._write("corsair_queen.amd", "Warlord", "warlord")
        got = self._dupes(copy)
        self.assertEqual(len(got), 1)
        self.assertIn("warlord.amd", got[0].message)
        self.assertEqual(got[0].line, 1)

    def test_both_files_are_told(self):
        """Whichever file the author has open is the one that has to say so."""
        first = self._write("warlord.amd", "Warlord", "warlord")
        self._write("corsair_queen.amd", "Warlord", "warlord")
        self.assertEqual(len(self._dupes(first)), 1)

    def test_a_renamed_copy_is_clean(self):
        self._write("warlord.amd", "Warlord", "warlord")
        copy = self._write("corsair_queen.amd", "Corsair Queen", "corsair_queen")
        self.assertEqual(self._dupes(copy), [])

    def test_a_key_may_repeat_it_is_the_name_the_list_uses(self):
        self._write("warlord.amd", "Warlord", "warlord")
        copy = self._write("corsair_queen.amd", "Corsair Queen", "warlord")
        self.assertEqual(self._dupes(copy), [])

    def test_a_neighbor_that_is_not_a_boss_does_not_count(self):
        self._write("notes.amd", "Warlord", "warlord", kind="Quest")
        boss = self._write("warlord.amd", "Warlord", "warlord")
        self.assertEqual(self._dupes(boss), [])

    def test_linting_bare_text_skips_the_check_instead_of_guessing(self):
        self._write("warlord.amd", "Warlord", "warlord")
        copy = self._write("corsair_queen.amd", "Warlord", "warlord")
        with open(copy, encoding="utf-8") as f:
            got = amd_lint(content=f.read())
        self.assertNotIn("duplicate-boss-name", _codes(got))


if __name__ == "__main__":
    unittest.main()
