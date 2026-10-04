"""Lint sees the SHAPE of a record the way the game does.

Found by two lessons, "The shape of a record" and "Lint is your editor". Each mistake here
is one a new writer makes in the first hour, and each one used to get `clean` from lint
while the game dropped the record - or got a finding that was false, or on the wrong line:

  * a heading with no space after the hashes, a space before them, a space between `]`
    and `(`, or no brackets at all: the record is gone, lint said nothing
  * a `---` scene break in a description: a false ERROR on the last line of the file
  * a deleted closing `---`: six findings, the true one last, naming the next record
  * a deleted opening `---`: one error, ten lines below, in the next record
  * `--`, `***` or one long dash where `---` goes
  * a field with a space in front of it, or written twice
  * `Done wen:` answered with the first six field names in a-b-c order

    python -m unittest tests.test_amd_lint_shape
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_lint import amd_lint, amd_lint_structural, ERROR, WARNING

MISSION = """# [Sample Mission](sample_mission)

## [Quests](quests)

### [First Contact](first_contact)
---
Scope: shared
Starts when: at once
---
A derelict has drifted into the sector.

#### [Find the Derelict](find)
---
Scope: shared
Starts when: at once
Done when: signal derelict_found
Then: reveal first_contact/study
---
Fly out and locate the drifting hulk.

#### [Study the Derelict](study)
---
Scope: shared
Starts when: revealed
Done when: signal derelict_studied
---
Science should take a full scan of the hull.

## [Scans](scans)

### [Derelict Hull](derelict_scan)
---
Scan of: derelict
Tab: scan
---
% The hull is cold.
% Hull plating is intact.

### [Derelict Materials](derelict_mat)
---
Scan of: derelict
Tab: mat
---
% Scoring along the plating.
"""

HULL = "### [Derelict Hull](derelict_scan)"
SHAPE = ("broken-heading", "suspect-heading", "unclosed-data-fence", "fence-not-opened",
         "fence-shape", "heading-level-jump", "no-headings", "field-indented",
         "repeated-field", "unknown-field", "duplicate-key", "dangling-reveal",
         "fence-syntax")


def line_of(text, needle, nth=1):
    hits = [i for i, l in enumerate(text.split("\n"), start=1) if l == needle]
    return hits[nth - 1]


def lint(text):
    """Every finding about shape, as (line, code), with the mission's own keys known."""
    found = amd_lint(content=text, known_keys=set(parse(text).keys), cross_file=False)
    return [f for f in found if f.code in SHAPE]


def one(test, text):
    found = lint(text)
    test.assertEqual(len(found), 1, [str(f) for f in found])
    return found[0]


class TheTemplateIsClean(unittest.TestCase):
    def test_no_finding_at_all(self):
        self.assertEqual([str(f) for f in lint(MISSION)], [])


class AHeadingTheGameDoesNotRead(unittest.TestCase):
    def broken(self, typed):
        text = MISSION.replace(HULL, typed)
        f = one(self, text)
        self.assertEqual((f.code, f.severity, f.line),
                         ("broken-heading", ERROR, line_of(text, typed)))
        return f.message

    def test_no_space_after_the_hashes(self):
        self.assertIn("no space between the hashes", self.broken("###[Derelict Hull](derelict_scan)"))

    def test_spaces_in_front_of_the_hashes(self):
        self.assertIn("2 spaces in front", self.broken("  ### [Derelict Hull](derelict_scan)"))

    def test_a_space_between_the_brackets(self):
        self.assertIn("space between `]` and `(`", self.broken("### [Derelict Hull] (derelict_scan)"))

    def test_no_closing_square_bracket(self):
        self.assertIn("fence under it", self.broken("### [Derelict Hull(derelict_scan)"))

    def test_no_square_brackets(self):
        self.assertIn("fence under it", self.broken("### Derelict Hull (derelict_scan)"))

    def test_no_closing_round_bracket(self):
        self.broken("### [Derelict Hull](derelict_scan")

    def test_a_heading_in_prose_is_left_alone(self):
        text = MISSION.replace("Fly out and locate", "## What you know\n\nFly out and locate")
        self.assertEqual(lint(text), [])

    def test_a_name_with_no_key_and_a_fence_under_it(self):
        self.assertIn("no `(key)`", self.broken("### [Derelict Hull]"))

    def test_the_hashes_left_off(self):
        message = self.broken("[Derelict Hull](derelict_scan)")
        self.assertIn("no hashes in front", message)
        self.assertNotIn("Move that line", message)

    def test_a_name_with_no_key_is_still_only_a_warning(self):
        text = MISSION.replace("Fly out and locate", "## [What you know]\n\nFly out and locate")
        f = one(self, text)
        self.assertEqual((f.code, f.severity), ("suspect-heading", WARNING))


class TheFence(unittest.TestCase):
    def test_a_scene_break_in_a_description_is_not_a_fence(self):
        text = MISSION.replace("Fly out and locate the drifting hulk.",
                               "Fly out.\n\n---\n\nLocate the drifting hulk.")
        self.assertEqual([str(f) for f in lint(text)], [])

    def test_a_missing_closing_line_is_named_where_the_fence_opens(self):
        text = MISSION.replace("Tab: scan\n---\n", "Tab: scan\n")
        first = one(self, text)          # ONE finding. It used to be the last of six.
        self.assertEqual((first.code, first.line),
                         ("unclosed-data-fence", line_of(text, HULL) + 1))
        self.assertIn("### [Derelict Materials](derelict_mat)", first.message)

    def test_what_a_broken_fence_drags_in_is_not_printed(self):
        text = MISSION.replace("Tab: scan\n---\n", "Tab: scan\n")
        codes = [f.code for f in amd_lint(content=text, known_keys=set(parse(text).keys),
                                          cross_file=False)]
        for code in ("fence-syntax", "field-below-fence", "fence-not-opened"):
            self.assertNotIn(code, codes)

    def test_a_finding_in_a_record_above_the_broken_fence_is_kept(self):
        text = MISSION.replace("Tab: scan\n---\n", "Tab: scan\n").replace(
            "Done when: signal derelict_found", "Done wen: signal derelict_found")
        self.assertEqual([f.code for f in lint(text)], ["unknown-field", "unclosed-data-fence"])

    def test_a_missing_opening_line_is_named_on_its_own_record(self):
        text = MISSION.replace(HULL + "\n---\n", HULL + "\n")
        found = [f for f in lint(text) if f.code == "fence-not-opened"]
        self.assertEqual([(f.line, f.severity) for f in found],
                         [(line_of(text, HULL) + 1, ERROR)])
        self.assertNotIn("unclosed-data-fence", [f.code for f in lint(text)])

    def test_a_sentence_above_the_fence(self):
        text = MISSION.replace(HULL + "\n---\n", HULL + "\nThe hulk, close up.\n---\n")
        found = [f for f in lint(text) if f.code == "fence-not-opened"]
        self.assertEqual([f.line for f in found], [line_of(text, HULL) + 2])
        self.assertIn("The hulk, close up.", found[0].message)

    def test_a_closing_line_typed_another_way(self):
        for typed in ("--", "___", "***", "- - -", "—"):
            with self.subTest(typed=typed):
                text = MISSION.replace("Tab: scan\n---\n", "Tab: scan\n" + typed + "\n")
                found = [f for f in lint(text) if f.code in ("fence-shape", "unclosed-data-fence")]
                self.assertEqual([(f.code, f.line) for f in found],
                                 [("fence-shape", line_of(text, "Tab: scan") + 1)])

    def test_an_opening_line_typed_another_way(self):
        text = MISSION.replace(HULL + "\n---\n", HULL + "\n--\n")
        found = [f for f in lint(text) if f.code == "fence-shape"]
        self.assertEqual([f.line for f in found], [line_of(text, HULL) + 1])

    def test_both_fence_lines_typed_another_way(self):
        # `fence-shape` used to need ONE good line to measure against.
        for typed in ("--", "***", "___", "- - -", "--- facts"):
            with self.subTest(typed=typed):
                text = MISSION.replace(HULL + "\n---\nScan of: derelict\nTab: scan\n---\n",
                                       HULL + f"\n{typed}\nScan of: derelict\nTab: scan\n{typed}\n")
                f = one(self, text)
                self.assertEqual((f.code, f.line), ("fence-shape", line_of(text, HULL) + 1))

    def test_both_fence_lines_left_out(self):
        text = MISSION.replace(HULL + "\n---\nScan of: derelict\nTab: scan\n---\n",
                               HULL + "\nScan of: derelict\nTab: scan\n")
        f = one(self, text)
        self.assertEqual((f.code, f.line), ("fence-not-opened", line_of(text, HULL) + 1))
        self.assertIn("no `---` lines round them", f.message)

    def test_a_description_that_opens_with_a_label_is_not_a_field(self):
        text = MISSION.replace("Fly out and locate the drifting hulk.",
                               "Note: the hulk is further out than it looks.")
        self.assertEqual([str(f) for f in lint(text)], [])

    def test_the_last_records_fence_left_open_is_one_finding(self):
        text = MISSION.replace("Tab: mat\n---\n", "Tab: mat\n")
        f = one(self, text)
        self.assertEqual(f.code, "unclosed-data-fence")

    def test_a_no_break_space_after_the_hashes_is_a_heading_to_the_game(self):
        # The game folds it to a space before it looks for headings. Lint read the raw
        # line, saw no heading, and reported a broken fence on a line below.
        text = MISSION.replace(HULL, "###" + chr(0xa0) + HULL[4:])
        self.assertEqual([f.code for f in amd_lint_structural(content=text)], [])

    def test_a_fence_left_open_at_the_end_of_the_file(self):
        text = MISSION.replace("Tab: mat\n---\n", "Tab: mat\n")
        found = [f for f in amd_lint_structural(content=text) if f.code == "unclosed-data-fence"]
        self.assertEqual([f.line for f in found],
                         [line_of(text, "### [Derelict Materials](derelict_mat)") + 1])


class TooManyHashes(unittest.TestCase):
    def test_it_says_how_many_and_what_the_game_does(self):
        text = MISSION.replace(HULL, "#" + HULL)
        f = one(self, text)
        self.assertEqual((f.code, f.severity), ("heading-level-jump", ERROR))
        self.assertIn("1 too many", f.message)
        self.assertIn("as if it had 3", f.message)

    def test_one_hash_on_a_record_is_named_on_that_record(self):
        text = MISSION.replace(HULL, HULL[2:])
        jumps = [f for f in amd_lint_structural(content=text) if f.code == "heading-level-jump"]
        self.assertEqual([f.line for f in jumps], [line_of(text, HULL[2:])])
        self.assertIn("has 1 hash", jumps[0].message)
        self.assertIn("Give it 3", jumps[0].message)

    def test_a_flat_file_of_one_hash_records_is_left_alone(self):
        text = ("# [Torgoth](torgoth)\n---\nSpeaker: torgoth\n---\nHello.\n\n"
                "## [Again](again)\nMore.\n\n"
                "# [Kralien](kralien)\n---\nSpeaker: kralien\n---\nHello.\n\n"
                "## [Again](again2)\nMore.\n")
        self.assertEqual(amd_lint_structural(content=text), [])

    def test_a_file_with_no_title(self):
        text = MISSION.replace("# [Sample Mission](sample_mission)\n", "")
        jumps = [f for f in amd_lint_structural(content=text) if f.code == "heading-level-jump"]
        self.assertEqual(len(jumps), 1)
        self.assertIn("no title", jumps[0].message)

    def test_an_empty_file(self):
        for text in ("", "\n\n", "Just some words.\n"):
            with self.subTest(text=text):
                found = amd_lint_structural(content=text)
                self.assertEqual([(f.code, f.severity) for f in found], [("no-headings", ERROR)])


class AFieldTheGameReadsAnotherWay(unittest.TestCase):
    def test_a_space_in_front_of_a_field(self):
        text = MISSION.replace("Done when: signal derelict_found", "  Done when: signal derelict_found")
        f = one(self, text)
        self.assertEqual((f.code, f.line),
                         ("field-indented", line_of(text, "  Done when: signal derelict_found")))
        self.assertIn("Starts when: at once", f.message)

    def test_a_tab_in_front_of_a_field(self):
        text = MISSION.replace("Tab: mat", "\tTab: mat")
        self.assertEqual(one(self, text).code, "field-indented")

    def test_a_wrapped_value_is_left_alone(self):
        text = MISSION.replace("Done when: signal derelict_found",
                               "Objective: Find the hulk\n  before it drifts: quickly\n"
                               "Done when: signal derelict_found")
        self.assertEqual([str(f) for f in lint(text)], [])

    def test_a_field_written_twice(self):
        text = MISSION.replace("Done when: signal derelict_found",
                               "Done when: signal derelict_found\nDone when: signal other")
        f = one(self, text)
        self.assertEqual((f.code, f.line), ("repeated-field", line_of(text, "Done when: signal other")))

    def test_a_misspelled_field_gets_a_guess(self):
        for typed, meant in (("Done wen", "Done when"), ("Scop", "Scope"), ("Tabb", "Tab")):
            with self.subTest(typed=typed):
                was = {"Done wen": "Done when: signal derelict_found",
                       "Scop": "Scope: shared\nStarts when: revealed",
                       "Tabb": "Tab: mat"}[typed]
                text = MISSION.replace(was, was.replace(meant, typed, 1))
                found = [f for f in lint(text) if f.code == "unknown-field"]
                self.assertEqual(len(found), 1)
                self.assertIn(f"Did you mean `{meant}`?", found[0].message)
                self.assertNotIn("amd_register_fields", found[0].message)

    def test_a_field_of_another_kind_points_at_the_section_heading(self):
        text = MISSION.replace("## [Scans](scans)\n", "")
        found = [f for f in lint(text) if f.code == "unknown-field"]
        self.assertTrue(found)
        self.assertIn("is a scan field", found[0].message)
        self.assertIn("read as a quest", found[0].message)


class ACharacterTheGameCannotDraw(unittest.TestCase):
    def said(self, body):
        from sbs_utils.procedural.amd_lint import amd_lint_ascii
        return [f.message for f in amd_lint_ascii(content="# [A](a)\n" + body + "\n")]

    def test_it_says_what_the_game_shows_instead(self):
        self.assertIn('shows `"` in its place', self.said("a “ghost”")[0])
        self.assertIn("shows `-` in its place", self.said("cold — dark")[0])
        self.assertIn("shows `e` in its place", self.said("café")[0])

    def test_one_it_cannot_fold_is_left_out(self):
        self.assertIn("leaves it out", self.said("launch \U0001F680")[0])

    def test_one_that_cannot_be_seen_is_named(self):
        message = self.said("a b")[0]
        self.assertIn("a no-break space", message)
        self.assertIn("plain space", message)

    def test_it_no_longer_says_crash(self):
        self.assertNotIn("crash", self.said("a “ghost”")[0])


class OneMistakeOneTrueLine(unittest.TestCase):
    def test_a_copied_step_is_a_duplicate_and_not_a_dangling_reveal(self):
        copy = ("\n#### [Study It Again](study)\n---\nScope: shared\nStarts when: revealed\n"
                "Done when: signal again\n---\nOnce more.\n")
        text = MISSION.replace("\n## [Scans](scans)", copy + "\n## [Scans](scans)")
        self.assertEqual([f.code for f in lint(text)], ["duplicate-key"])

    def test_a_renamed_arc_is_caught_and_the_fix_is_named(self):
        text = MISSION.replace("(first_contact)", "(contact)")
        f = one(self, text)
        self.assertEqual((f.code, f.line),
                         ("dangling-reveal", line_of(text, "Then: reveal first_contact/study")))
        self.assertIn("write `Then: reveal contact/study`", f.message)

    def test_a_path_into_another_file_is_still_trusted(self):
        text = MISSION.replace("Then: reveal first_contact/study", "Then: reveal other_arc/next")
        found = amd_lint(content=text, cross_file=False,
                         known_keys=set(parse(text).keys) | {"other_arc", "next"})
        self.assertNotIn("dangling-reveal", [f.code for f in found])


if __name__ == "__main__":
    unittest.main()
