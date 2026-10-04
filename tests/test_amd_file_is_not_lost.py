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
