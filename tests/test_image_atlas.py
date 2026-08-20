"""Atlas registration - domains, and cutting a sheet into cells.

    python -m unittest tests.test_image_atlas
"""
from sbs_utils.fs import test_set_exe_dir, get_script_dir
test_set_exe_dir()

import os
import struct
import unittest
import zlib

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.gui.image import (ImageAtlas, gui_image_add_atlas,
                                            gui_image_add_atlas_grid, gui_image_get_atlas)

SHEET = "media/icons/quest-sheet"


def _png(width, height):
    """The smallest real PNG of a given size - the size test reads the actual header."""
    def chunk(kind, body):
        block = kind + body
        return (struct.pack(">I", len(body)) + block
                + struct.pack(">I", zlib.crc32(block) & 0xffffffff))
    row = bytes([0]) + bytes(width * 3)          # filter byte, then RGB pixels
    signature = bytes([137, 80, 78, 71, 13, 10, 26, 10])
    return (signature
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height))
            + chunk(b"IEND", b""))


class Domains(unittest.TestCase):
    """`ImageAtlas.all` is ONE process-wide dict. Two addons that both register
    `card_back` collide, and the last one loaded silently wins."""

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self._saved = dict(ImageAtlas.all)

    def tearDown(self):
        ImageAtlas.all.clear()
        ImageAtlas.all.update(self._saved)

    def test_two_addons_can_claim_the_same_word(self):
        gui_image_add_atlas("card_back", SHEET, 0, 0, 8, 8, domain="casino")
        gui_image_add_atlas("card_back", SHEET, 8, 0, 16, 8, domain="tarot")
        self.assertEqual(gui_image_get_atlas("card_back", "casino").left, 0)
        self.assertEqual(gui_image_get_atlas("card_back", "tarot").left, 8)

    def test_a_domain_does_not_answer_a_bare_lookup(self):
        """Scoping has to be real in both directions, or a domain is decoration: a bare
        key must not find a domained registration."""
        gui_image_add_atlas("card_back", SHEET, 0, 0, 8, 8, domain="casino")
        self.assertNotIn("card_back", ImageAtlas.all)
        self.assertIn("casino:card_back", ImageAtlas.all)

    def test_no_domain_behaves_exactly_as_before(self):
        gui_image_add_atlas("plain", SHEET)
        self.assertIn("plain", ImageAtlas.all)
        self.assertIs(gui_image_get_atlas("plain"), ImageAtlas.all["plain"])


class CuttingUpASheet(unittest.TestCase):
    """The same four lines of cell arithmetic every time, and an error in one shows up as
    art off by a cell rather than as a failure."""

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self._saved = dict(ImageAtlas.all)

    def tearDown(self):
        ImageAtlas.all.clear()
        ImageAtlas.all.update(self._saved)

    def test_names_are_laid_out_row_major(self):
        out = gui_image_add_atlas_grid(SHEET, 4, 4, ["a", "b", "c", "d", "e"], cell=64)
        self.assertEqual((out["a"].left, out["a"].top), (0, 0))
        self.assertEqual((out["d"].left, out["d"].top), (192, 0))
        self.assertEqual((out["e"].left, out["e"].top), (0, 64))     # wrapped a row
        self.assertEqual((out["e"].right, out["e"].bottom), (64, 128))

    def test_a_none_entry_skips_a_cell(self):
        """A sheet in progress has gaps; renumbering every later name to close one is how
        a sheet and its names drift apart."""
        out = gui_image_add_atlas_grid(SHEET, 4, 4, ["a", None, "c"], cell=64)
        self.assertNotIn(None, out)
        self.assertEqual(out["c"].left, 128)

    def test_a_dict_places_a_sparse_sheet(self):
        out = gui_image_add_atlas_grid(SHEET, 8, 8, {"job": (2, 3)}, cell=64)
        self.assertEqual((out["job"].left, out["job"].top), (128, 192))

    def test_start_offsets_the_first_name(self):
        out = gui_image_add_atlas_grid(SHEET, 4, 4, ["a"], cell=64, start=5)
        self.assertEqual((out["a"].left, out["a"].top), (64, 64))

    def test_non_square_cells(self):
        out = gui_image_add_atlas_grid(SHEET, 3, 2, ["a", "b"], cell=(190, 280))
        self.assertEqual((out["b"].left, out["b"].right), (190, 380))
        self.assertEqual(out["b"].bottom, 280)

    def test_the_cell_size_is_measured_from_the_sheet(self):
        """Asking the author to repeat what the art already says is one more thing that
        can disagree with it."""
        original = ImageAtlas.get_size
        ImageAtlas.get_size = lambda self: (512, 256)
        try:
            out = gui_image_add_atlas_grid(SHEET, 8, 4, ["a", "b"])
        finally:
            ImageAtlas.get_size = original
        self.assertEqual((out["a"].right, out["a"].bottom), (64, 64))
        self.assertEqual(out["b"].left, 64)

    def test_an_unmeasurable_sheet_says_so(self):
        original = ImageAtlas.get_size
        ImageAtlas.get_size = lambda self: (None, None)
        try:
            with self.assertRaises(ValueError):
                gui_image_add_atlas_grid(SHEET, 8, 4, ["a"])
        finally:
            ImageAtlas.get_size = original

    def test_a_grid_can_be_domained(self):
        gui_image_add_atlas_grid(SHEET, 4, 4, ["job"], cell=64, domain="icon")
        self.assertIn("icon:job", ImageAtlas.all)


class FindingTheFileAgain(unittest.TestCase):
    """`self.file` is what the ENGINE is handed. Everything on this side that has to
    OPEN the art - the exists check behind "IMAGE NOT FOUND", and the header read that
    measures it - has to resolve that same string back to a real path.

    The two drifted apart once: `self.file` moved to `engine_file` shape (relative to the
    Cosmos root) while both readers went on joining it onto `data/graphics`, so every
    mission image reported itself missing and measured nothing.
    """

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self._saved = dict(ImageAtlas.all)
        # A real 3x2 PNG in the mission, because the header read is the point.
        self.rel = "media/probe/atlas_probe"
        self.path = os.path.join(get_script_dir(), *self.rel.split("/")) + ".png"
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "wb") as f:
            f.write(_png(3, 2))

    def tearDown(self):
        ImageAtlas.all.clear()
        ImageAtlas.all.update(self._saved)
        os.remove(self.path)
        os.rmdir(os.path.dirname(self.path))

    def test_mission_art_is_named_from_the_cosmos_root(self):
        atlas = ImageAtlas(None, self.rel)
        self.assertFalse(os.path.isabs(atlas.file))
        self.assertTrue(atlas.file.startswith("data/"), atlas.file)
        self.assertNotIn(chr(92), atlas.file)

    def test_mission_art_is_found_and_measured(self):
        atlas = ImageAtlas(None, self.rel)
        self.assertTrue(atlas.is_valid(), atlas.file)
        self.assertEqual(atlas.get_size(), (3, 2))

    def test_local_file_resolves_what_the_engine_was_given(self):
        atlas = ImageAtlas(None, self.rel)
        self.assertEqual(os.path.normpath(atlas.local_file() + ".png"),
                         os.path.normpath(self.path))

    def test_art_that_is_not_there_still_says_so(self):
        self.assertFalse(ImageAtlas(None, "media/probe/no_such_art").is_valid())


if __name__ == "__main__":
    unittest.main()
