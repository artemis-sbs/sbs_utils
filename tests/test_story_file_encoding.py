"""A story in a folder is read as UTF-8, the same as one in a mastlib.

Found by the lesson "Just enough MAST". `story.mast` was opened with the machine's own
code page. On Windows one curly quote pasted from a word processor - in a COMMENT - is a
byte that page has no letter for: `'charmap' codec can't decode byte 0x9d`, no line
number, and a story that never started. The same file packed in a mastlib loaded.

    python -m unittest tests.test_story_file_encoding
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (always import explicitly)
from sbs_utils.mast.mast import Mast

STORY = "# It is the captain’s log, “as written”.\nx = 1\n== later ==\ny = 2\n"


class StoryEncodingTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def load(self, data):
        path = os.path.join(self.dir.name, "story.mast")
        with open(path, "wb") as f:
            f.write(data)
        mast = Mast()
        mast.basedir = self.dir.name
        return mast, mast.content_from_lib_or_file("story.mast")

    def test_curly_quotes_saved_as_utf8_load(self):
        _mast, (content, errors) = self.load(STORY.encode("utf-8"))
        self.assertIsNone(errors)
        self.assertEqual(content, STORY)

    def test_the_story_then_compiles(self):
        mast, (content, errors) = self.load(STORY.encode("utf-8"))
        self.assertIsNone(errors)
        self.assertEqual(mast.compile(content, "story.mast", mast), [])
        self.assertIn("later", mast.labels)

    def test_a_byte_order_mark_and_windows_line_endings_are_taken_off(self):
        data = b"\xef\xbb\xbf" + STORY.replace("\n", "\r\n").encode("utf-8")
        _mast, (content, errors) = self.load(data)
        self.assertIsNone(errors)
        self.assertEqual(content, STORY)

    def test_a_file_saved_in_the_old_code_page_still_loads(self):
        # 0x92 is a curly apostrophe in Windows-1252 and is not UTF-8 at all.
        _mast, (content, errors) = self.load(b"# the captain\x92s log\nx = 1\n")
        self.assertIsNone(errors)
        self.assertIn("x = 1", content)


if __name__ == "__main__":
    unittest.main()
