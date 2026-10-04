"""One beginner's mistake must not cost the whole file.

Found by the lesson "The shape of a record". Each of these made the game read NOTHING from
`mission.amd` - no quests, no readings - with lint clean or nearly so, and for the second
a passing run and an empty log:

  * `### [Derelict Intel](derelict_intel?)` - a question mark in ONE key. The reader raised
    on it and the whole document came back as an error stub.
  * the file saved as UTF-16 (Notepad's "Unicode"). It was decoded as cp1252, a NUL after
    every letter, and no heading matched.

Also here: a tool that builds a Mast to check a story must not empty the mission's logs.

    python -m unittest tests.test_amd_file_is_not_lost
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils import fs
from sbs_utils.mast.mast import Mast
from sbs_utils.procedural.amd import amd_read_text
from sbs_utils.procedural.amd_doc import amd_section
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.quest import document_get_amd_file

MISSION = """# [Sample Mission](sample_mission)

## [Quests](quests)

### [First Contact](first_contact)
---
Scope: shared
Starts when: at once
Done when: signal derelict_found
---
A dead ship has drifted across the border.

## [Scans](scans)

### [Derelict Intel]({key})
---
Scan of: derelict
Tab: intel
---
% No flight plan was ever filed for this ship.
"""


class _Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, text, encoding="utf-8"):
        path = os.path.join(self.dir.name, "mission.amd")
        with open(path, "wb") as f:
            f.write(text.encode(encoding))
        return path

    def keys(self, path, section):
        doc = document_get_amd_file(path, data_parser=amd_quest_data)
        node = amd_section(doc, section)
        return [c.get("key") for c in (node or {}).get("children", [])]


class AQuestionMarkInOneKey(_Files):
    def test_the_file_is_still_read(self):
        path = self.write(MISSION.format(key="derelict_intel?"))
        self.assertEqual(self.keys(path, "quests"), ["first_contact"])
        self.assertEqual(self.keys(path, "scans"), ["derelict_intel"])

    def test_a_real_query_is_still_a_query(self):
        path = self.write(MISSION.format(key="derelict_intel?tone=cold"))
        self.assertEqual(self.keys(path, "scans"), ["derelict_intel"])


class AFileSavedAsUtf16(_Files):
    def test_both_byte_orders_are_read(self):
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            with self.subTest(encoding=encoding):
                text = MISSION.format(key="derelict_intel")
                if encoding == "utf-16":
                    path = self.write(text, "utf-16")              # with its own mark
                else:
                    mark = b"\xff\xfe" if encoding.endswith("le") else b"\xfe\xff"
                    path = os.path.join(self.dir.name, "mission.amd")
                    with open(path, "wb") as f:
                        f.write(mark + text.encode(encoding))
                self.assertEqual(amd_read_text(path).replace("\r\n", "\n"), text)
                self.assertEqual(self.keys(path, "quests"), ["first_contact"])

    def test_utf8_and_the_old_code_page_are_unchanged(self):
        text = MISSION.format(key="derelict_intel")
        self.assertEqual(amd_read_text(self.write(text)), text)
        self.assertEqual(amd_read_text(self.write("﻿" + text)), text)
        legacy = text.replace("drifted", "drifted ’round")
        self.assertEqual(amd_read_text(self.write(legacy, "cp1252")), legacy)


class _Said(_Files):
    """Collects what the reader reports, the way cosmos_dev's verdict does."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural import amd_error
        from sbs_utils.procedural.quest import amd_doc_cache_clear
        amd_doc_cache_clear()             # each test is a new mission
        self.said = []
        self.addCleanup(setattr, amd_error, "on_amd_error", amd_error.on_amd_error)
        amd_error.on_amd_error = lambda msg, path, line, sev: self.said.append((line, sev, msg))

    def doc(self, text):
        return document_get_amd_file(None, content=text, data_parser=amd_quest_data)

    def children(self, text, section):
        return [c.get("key") for c in (amd_section(self.doc(text), section) or {}).get("children", [])]


class OneHashTooMany(_Said):
    """Found by "Lint is your editor". `#### [Derelict Intel]` straight under `##` was a raw
    IndexError: no quests, no readings, and `list assignment index out of range` in the log."""

    def test_the_file_is_still_read_and_the_record_lands_in_its_section(self):
        text = MISSION.format(key="derelict_intel").replace("### [Derelict Intel]", "#### [Derelict Intel]")
        self.assertEqual(self.children(text, "quests"), ["first_contact"])
        self.assertEqual(self.children(text, "scans"), ["derelict_intel"])

    def test_it_is_named_once_with_its_line(self):
        text = MISSION.format(key="derelict_intel").replace("### [Derelict Intel]", "#### [Derelict Intel]")
        self.doc(text)
        self.assertEqual([(line, sev) for line, sev, _ in self.said], [(15, "error")])
        self.assertIn("4 hashes", self.said[0][2])
        self.assertIn("at most 3", self.said[0][2])

    def test_a_story_that_loads_the_file_four_times_is_told_once(self):
        # Seen in the engine: quests, readings, places and crew each load the file,
        # and the log held four copies of the one sentence.
        text = MISSION.format(key="derelict_intel").replace("### [Derelict Intel]", "#### [Derelict Intel]")
        from sbs_utils.procedural.amd_mission import amd_mission_data
        for parser in (amd_quest_data, amd_mission_data, None):
            document_get_amd_file(None, content=text, data_parser=parser)
        document_get_amd_file(self.write(text), data_parser=amd_quest_data)
        self.assertEqual(len(self.said), 1)

    def test_one_hash_on_a_record_is_blamed_on_that_record(self):
        # The log used to name the NEXT record and say "take the extra off".
        text = MISSION.format(key="derelict_intel").replace("### [Derelict Intel]", "# [Derelict Intel]")
        text += "\n### [Derelict Materials](derelict_mat)\n---\nScan of: derelict\nTab: mat\n---\n% Scoring.\n"
        self.doc(text)
        self.assertEqual([line for line, _sev, _msg in self.said], [15])
        self.assertIn("has 1 hash", self.said[0][2])
        self.assertIn("Give it 3", self.said[0][2])

    def test_a_record_after_it_is_a_neighbor_not_a_child(self):
        text = MISSION.format(key="derelict_intel").replace("### [Derelict Intel]", "#### [Derelict Intel]")
        text += "\n### [Derelict Materials](derelict_mat)\n---\nScan of: derelict\nTab: mat\n---\n% Scoring.\n"
        self.assertEqual(self.children(text, "scans"), ["derelict_intel", "derelict_mat"])

    def test_a_well_formed_file_says_nothing(self):
        self.doc(MISSION.format(key="derelict_intel"))
        self.assertEqual(self.said, [])

    def test_the_tools_nest_it_the_same_way(self):
        from sbs_utils.procedural.amd_core import parse
        text = MISSION.format(key="derelict_intel").replace("### [Derelict Intel]", "#### [Derelict Intel]")
        text += "\n### [Derelict Materials](derelict_mat)\n---\nScan of: derelict\nTab: mat\n---\n% Scoring.\n"
        by_key = {n.key: n for n in parse(text).nodes}
        self.assertEqual(by_key["derelict_intel"].parent.key, "scans")
        self.assertEqual(by_key["derelict_mat"].parent.key, "scans")


class AFenceWithNoClosingLine(_Said):
    """A heading closes an open fence. The format reference and the scanner's own notes
    said so; the code tested "inside a fence" first, so the NEXT record's heading was read
    as a field and its fence finished the job. One missing line cost two records."""

    TWO = MISSION.format(key="derelict_intel") + (
        "\n### [Derelict Materials](derelict_mat)\n---\nScan of: derelict\nTab: mat\n---\n"
        "% Scoring along the plating.\n")
    OPEN = TWO.replace("Tab: intel\n---\n", "Tab: intel\n")

    def scans(self, text):
        return {c["key"]: c for c in amd_section(self.doc(text), "scans")["children"]}

    def test_the_next_record_is_untouched(self):
        scans = self.scans(self.OPEN)
        self.assertEqual(sorted(scans), ["derelict_intel", "derelict_mat"])
        self.assertEqual(scans["derelict_mat"]["data"].get("tab"), "mat")
        self.assertIn("Scoring along the plating", scans["derelict_mat"]["description"])

    def test_the_record_keeps_the_fields_it_did_write(self):
        self.assertEqual(self.scans(self.OPEN)["derelict_intel"]["data"].get("tab"), "intel")

    def test_it_is_an_error_named_on_the_line_the_fence_opens(self):
        self.doc(self.OPEN)
        errors = [(line, msg) for line, sev, msg in self.said if sev == "error"]
        self.assertEqual([line for line, _ in errors], [16])
        self.assertIn("no closing `---`", errors[0][1])
        self.assertIn("### [Derelict Materials](derelict_mat)", errors[0][1])

    def test_the_tools_read_it_the_same_way(self):
        from sbs_utils.procedural.amd_core import parse
        by_key = {n.key: n for n in parse(self.OPEN).nodes}
        self.assertEqual(by_key["derelict_mat"].data.get("tab"), "mat")
        self.assertEqual(by_key["derelict_mat"].parent.key, "scans")

    def test_a_closed_fence_is_as_it_was(self):
        self.doc(self.TWO)
        self.assertEqual(self.said, [])
        self.assertIn("No flight plan", self.scans(self.TWO)["derelict_intel"]["description"])


class TextTheEngineCanDraw(_Said):
    """Measured in the engine, 2026-10-04: one curly quote in a quest's text painted the whole
    font sheet across Helm, and one long dash in a reading did the same to Science."""

    CURLY = MISSION.format(key="derelict_intel").replace(
        "A dead ship has drifted across the border.",
        "Find the “ghost ship”. It isn’t answering — yet…")

    def quest_text(self, text):
        return amd_section(self.doc(text), "quests")["children"][0]["description"].strip()

    def test_typographic_marks_become_plain_ones(self):
        self.assertEqual(self.quest_text(self.CURLY),
                         'Find the "ghost ship". It isn\'t answering - yet...')

    def test_nothing_the_game_reads_is_outside_ascii(self):
        text = self.CURLY.replace("[First Contact]", "[Première Rencontre ☃]")
        node = amd_section(self.doc(text), "quests")["children"][0]
        self.assertEqual(node["display_text"], "Premiere Rencontre ")
        self.assertTrue(node["description"].isascii())

    def test_an_ascii_file_is_handed_back_untouched(self):
        from sbs_utils.procedural.amd import amd_ascii_text
        line = "A dead ship has drifted across the border."
        self.assertIs(amd_ascii_text(line), line)

    def test_the_switch_puts_it_back(self):
        from sbs_utils.procedural import amd
        from sbs_utils.procedural.quest import amd_doc_cache_clear
        self.addCleanup(setattr, amd, "AMD_ASCII_TEXT", amd.AMD_ASCII_TEXT)
        self.addCleanup(amd_doc_cache_clear)
        amd.AMD_ASCII_TEXT = False
        amd_doc_cache_clear()
        self.assertIn("“ghost ship”", self.quest_text(self.CURLY))

    def test_lint_still_names_every_one(self):
        from sbs_utils.procedural.amd_lint import amd_lint_ascii
        found = amd_lint_ascii(content=self.CURLY)
        self.assertEqual([f.code for f in found], ["non-ascii"] * 5)


class ANoteThatIsTabbedIn(_Said):
    def test_the_crew_is_not_shown_it(self):
        text = MISSION.format(key="derelict_intel").replace(
            "A dead ship has drifted across the border.",
            "A dead ship has drifted across the border.\n    // ask Doug about the name")
        body = amd_section(self.doc(text), "quests")["children"][0]["description"]
        self.assertNotIn("ask Doug", body)
        self.assertIn("A dead ship", body)


class ASectionKeyWithACapital(_Said):
    def test_it_is_the_section_it_plainly_is(self):
        text = MISSION.format(key="derelict_intel").replace("[Scans](scans)", "[Scans](Scans)")
        self.assertEqual(self.children(text, "scans"), ["derelict_intel"])

    def test_an_exact_key_still_wins(self):
        text = MISSION.format(key="derelict_intel") + "\n## [Other](Scans)\n\n### [X](x)\n"
        self.assertEqual(self.children(text, "scans"), ["derelict_intel"])


class AToolLeavesTheLogsAlone(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        real = fs.get_mission_dir_filename
        fs.get_mission_dir_filename = lambda name: os.path.join(self.dir.name, name)
        self.addCleanup(setattr, fs, "get_mission_dir_filename", real)
        self.addCleanup(setattr, Mast, "leave_logs_alone", Mast.leave_logs_alone)
        self.log = os.path.join(self.dir.name, "mast.runtime.log")
        with open(self.log, "w") as f:
            f.write("what the last game said\n")

    def close_handlers(self):
        import logging
        for name in ("mast.compile", "mast.runtime"):
            log = logging.getLogger(name)
            for handler in list(log.handlers):
                if isinstance(handler, logging.FileHandler):
                    log.removeHandler(handler)
                    handler.close()

    def read(self):
        with open(self.log) as f:
            return f.read()

    def test_a_tool_does_not_empty_the_log(self):
        Mast.leave_logs_alone = True
        Mast()
        self.close_handlers()
        self.assertEqual(self.read(), "what the last game said\n")

    def test_a_game_run_still_starts_with_an_empty_log(self):
        Mast.leave_logs_alone = False
        Mast()
        self.close_handlers()
        self.assertEqual(self.read(), "")


if __name__ == "__main__":
    unittest.main()
