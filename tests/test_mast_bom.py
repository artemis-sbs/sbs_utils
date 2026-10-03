"""A file saved with a byte-order mark still compiles.

Found while probing a lesson mission: one PowerShell `Set-Content -Encoding utf8` put three
invisible bytes at the front of a helper file, and the whole story compiled to nothing -

    Error: Unrecognized syntax; no MAST node matched this line
    at story.mast Line 1 - '\\ufeff#'

Older Notepad does the same when asked for UTF-8. No editor shows the character, the line
it is reported against looks perfect, and a story that does not compile schedules no task
at all. An author who has never seen a command prompt has no way back from that.

    python -m unittest tests.test_mast_bom
"""
import os
import shutil
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast_sbs import story_nodes  # noqa: F401 - register the node types
from sbs_utils.mast.mast import Mast, strip_bom
from sbs_utils.mast.mast_globals import MastGlobals

BOM = b"\xef\xbb\xbf"


class StripBomTests(unittest.TestCase):
    def test_the_mark_as_one_character(self):
        self.assertEqual(strip_bom("﻿# a comment"), "# a comment")

    def test_the_mark_read_with_the_platform_encoding(self):
        # The same three bytes through cp1252 or latin-1, which is how a folder file is
        # read on a machine whose default encoding is not UTF-8.
        self.assertEqual(strip_bom(BOM.decode("latin-1") + "x = 1"), "x = 1")

    def test_a_file_without_one_is_untouched(self):
        self.assertEqual(strip_bom("x = 1\n"), "x = 1\n")
        self.assertEqual(strip_bom(""), "")

    def test_only_the_front_is_touched(self):
        self.assertEqual(strip_bom("x = '﻿'"), "x = '﻿'")


class AMarkedFileCompilesTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="mast_bom_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def put(self, name, text, bom=True):
        with open(os.path.join(self.dir, name), "wb") as f:
            f.write((BOM if bom else b"") + text.encode("utf-8"))

    def compile(self, source):
        story = Mast()
        story.basedir = self.dir
        return story, story.compile(source, "harness", story)

    def test_a_mast_file_with_a_mark(self):
        self.put("marked.mast", "# first line is a comment\n== marked_label ==\n    x = 1\n    ->END\n")
        story, errors = self.compile("import marked.mast\n")
        self.assertEqual(errors, [])
        self.assertIn("marked_label", story.labels)

    def test_the_same_file_without_one(self):
        self.put("plain.mast", "# first line is a comment\n== plain_label ==\n    ->END\n", bom=False)
        story, errors = self.compile("import plain.mast\n")
        self.assertEqual(errors, [])
        self.assertIn("plain_label", story.labels)

    def test_a_python_file_with_a_mark(self):
        self.put("bom_helper_file.py", "def bom_helper_marked():\n    return 7\n")
        self.addCleanup(MastGlobals.globals.pop, "bom_helper_marked", None)
        _story, errors = self.compile("import bom_helper_file.py\n")
        self.assertEqual(errors, [])
        self.assertIn("bom_helper_marked", MastGlobals.globals)


if __name__ == "__main__":
    unittest.main()
