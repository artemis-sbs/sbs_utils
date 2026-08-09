"""One decode: a .amd read from a folder and from a mastlib must be the same string.

The CRLF half of this lesson is already recorded on RE_HEADING in procedural/amd.py --
one file, two readers, two different documents. The ENCODING half stayed open: a folder
read used bare `open(path, "r")`, which decodes with the machine's LOCALE CODEPAGE,
while every zip read forces UTF-8. So the same bytes decoded two ways the moment the
file held a non-ASCII character, and on a codepage that rejects the byte the folder read
RAISED -- straight into the bare `except` in document_get_amd_file, which turns any
exception into an empty document. A blank panel, no log, and PASS.
"""
import io
import os
import tempfile
import unittest
import zipfile

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd import amd_read_text
from sbs_utils.procedural.media import media_read_from_zip
from sbs_utils.procedural.quest import document_get_amd_file


# Curly quotes, an em dash, an accent and a degree sign: all >1 byte in UTF-8 and
# all decoded differently (or not at all) by a legacy codepage.
SOURCE = (
    "# [Cafe Verdant](verdant)\n"
    "The owner’s name is René — he keeps a 30° list to port.\n"
)


class TestAmdEncoding(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "verdant.amd")
        with open(self.path, "wb") as f:
            f.write(SOURCE.encode("utf-8"))

    def test_folder_read_matches_zip_read(self):
        zpath = os.path.join(self.dir, "pack.mastlib")
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("verdant.amd", SOURCE.encode("utf-8"))
        self.assertEqual(amd_read_text(self.path),
                         media_read_from_zip(zpath, "verdant.amd"))

    def test_folder_read_round_trips_utf8(self):
        self.assertEqual(amd_read_text(self.path), SOURCE)

    def test_bom_is_stripped(self):
        p = os.path.join(self.dir, "bom.amd")
        with open(p, "wb") as f:
            f.write(SOURCE.encode("utf-8-sig"))
        # An editor-added BOM must not become part of the first heading, which is
        # how it would arrive: `﻿# [Cafe...` matches no heading rule at all.
        self.assertEqual(amd_read_text(p), SOURCE)

    def test_cp1252_file_still_decodes(self):
        # A legacy file that predates the UTF-8 convention must not raise; the
        # point of the fallback is that it parses rather than vanishing.
        p = os.path.join(self.dir, "legacy.amd")
        with open(p, "wb") as f:
            f.write("# [Café](cafe)\n".encode("cp1252"))
        self.assertEqual(amd_read_text(p), "# [Café](cafe)\n")

    def test_undecodable_bytes_do_not_raise(self):
        p = os.path.join(self.dir, "broken.amd")
        with open(p, "wb") as f:
            f.write(b"# [Bad](bad)\n\x81\x8d\x8f body\n")
        self.assertIn("[Bad](bad)", amd_read_text(p))

    def test_parsing_by_path_matches_parsing_by_content(self):
        # The whole point: file_path and content= are two doors into the same
        # parser and must not produce two different documents.
        by_path = document_get_amd_file(self.path, "root")
        by_text = document_get_amd_file(None, "root", content=SOURCE)
        self.assertEqual(len(by_path.get("children")), 1)
        self.assertEqual(by_path["children"][0].get("display_text"),
                         by_text["children"][0].get("display_text"))
        self.assertEqual(by_path["children"][0].get("description"),
                         by_text["children"][0].get("description"))


if __name__ == "__main__":
    unittest.main()
