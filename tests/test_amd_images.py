"""Declarative image atlases (and icons) from AMD.

    python -m unittest tests.test_amd_images
"""
import os
import struct
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_images import (images_declare_amd, images_declare_document,
                                             images_from_section, images_validate,
                                             images_sections)
from sbs_utils.procedural.gui.image import ImageAtlas
from sbs_utils.procedural.gui.icon_sheet import icon_resolve

ICONS = """# [Pack](pack)
---
Universe
---

## [Icons](icons)
---
icons
Sheet: icons/quest-sheet
Cell: 64
---
The quest log's glyphs.

### [Job](wanted)
---
At: 0, 0
---

### [Beat](talks)
---
At: 1, 2
Color: #888
---
"""

CARDS = """# [Deck](deck)
---
Universe
---

## [Cards](cards)
---
images
Sheet: casino/terran_deck
Cell: 190, 280
Domain: casino
---

### [Back](card_back)
---
At: 0, 0
---

### [Console](console_bg)
---
Sheet: helm/consoles0001
---
"""


class Base(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self._saved = dict(ImageAtlas.all)

    def tearDown(self):
        ImageAtlas.all.clear()
        ImageAtlas.all.update(self._saved)

    def section(self, text, key):
        # A document needs its `#` root - a file that starts at `##` parses to nothing,
        # so a fixture that is only a section has to be given one.
        if not text.lstrip().startswith("# "):
            text = "# [Pack](pack)\n---\nUniverse\n---\n\n" + text
        doc = amd_document(text)
        for node in images_sections(doc):
            if node.get("key") == key:
                return node
        self.fail(f"no atlas section {key!r} in the document")


class ASectionCarriesWhatEveryCellShares(Base):
    """The point of authoring a sheet: the sheet, the cell size and the domain are
    written ONCE, so an entry is a single `At:` line."""

    def test_entries_inherit_the_sheet_and_cell(self):
        records = images_from_section(self.section(ICONS, "icons"))
        self.assertEqual([r.get("key") for r in records], ["wanted", "talks"])
        self.assertTrue(records[0].get("sheet").endswith("icons/quest-sheet"))
        self.assertEqual(records[0].get("cell"), (64, 64))

    def test_at_becomes_pixels(self):
        out = images_declare_amd(self.section(ICONS, "icons"))
        self.assertEqual((out["talks"].left, out["talks"].top), (64, 128))
        self.assertEqual((out["talks"].right, out["talks"].bottom), (128, 192))

    def test_a_per_entry_color_survives(self):
        out = images_declare_amd(self.section(ICONS, "icons"))
        self.assertIn("color:#888", out["talks"].get_props())

    def test_a_non_square_cell(self):
        out = images_declare_amd(self.section(CARDS, "cards"))
        self.assertEqual((out["card_back"].right, out["card_back"].bottom), (190, 280))

    def test_an_entry_may_take_a_whole_file(self):
        """A loose image among cells - which is why `Sheet:` is overridable per entry."""
        out = images_declare_amd(self.section(CARDS, "cards"))
        self.assertIsNone(out["console_bg"].left)
        self.assertTrue(out["console_bg"].file.endswith("consoles0001"))


class IconsAreAtlasCellsInTheIconDomain(Base):
    """One archetype, two section words. What makes an icon an icon is only WHERE it is
    registered - which is what lets a mission re-skin the quest log by naming a look."""

    def test_an_icons_section_claims_the_look(self):
        self.assertEqual(icon_resolve("quest.job"), (111, None))   # built-in, before
        images_declare_amd(self.section(ICONS, "icons"))
        self.assertEqual(icon_resolve("quest.job"), (None, "icon:wanted"))

    def test_an_images_section_does_NOT_claim_icon_looks(self):
        """The guard, end to end: an ordinary sheet with an entry called `wanted` must not
        silently re-skin every quest log in the game."""
        doc = "## [Art](art)\n---\nimages\nSheet: art/misc\nCell: 32\n---\n\n" \
              "### [Wanted poster](wanted)\n---\nAt: 0, 0\n---\n"
        images_declare_amd(self.section(doc, "art"))
        self.assertIn("wanted", ImageAtlas.all)
        self.assertEqual(icon_resolve("quest.job"), (111, None))

    def test_a_named_domain_scopes_ordinary_keys(self):
        images_declare_amd(self.section(CARDS, "cards"))
        self.assertIn("casino:card_back", ImageAtlas.all)
        self.assertNotIn("card_back", ImageAtlas.all)


class WholeDocuments(Base):
    def test_every_section_in_a_document_declares(self):
        out = images_declare_document(amd_document(ICONS + "\n" + CARDS))
        self.assertEqual(set(out), {"wanted", "talks", "card_back", "console_bg"})

    def test_a_document_with_no_atlas_section_is_fine(self):
        doc = amd_document("# [Q](q)\n---\nQuest\n---\nProse.\n")
        self.assertEqual(images_declare_document(doc), {})


class WhatLintCatches(Base):
    """Every one of these renders as a blank widget today, silently."""

    def test_a_missing_sheet_file_is_an_error(self):
        records = images_from_section(self.section(ICONS, "icons"))
        codes = [c for _k, _s, c, _m in images_validate(records)]
        self.assertIn("image-missing-file", codes)

    def test_at_without_a_cell_size_is_an_error(self):
        """`At: 0, 0` means nothing until something says how big a cell is - and today
        that record silently registers no rect and draws the whole sheet."""
        doc = "## [Icons](icons)\n---\nicons\nSheet: icons/sheet\n---\n\n" \
              "### [Job](wanted)\n---\nAt: 0, 0\n---\n"
        records = images_from_section(self.section(doc, "icons"))
        real = ImageAtlas.is_valid
        ImageAtlas.is_valid = lambda self: True      # past the on-disk check, to this one
        try:
            codes = [c for _k, _s, c, _m in images_validate(records)]
        finally:
            ImageAtlas.is_valid = real
        self.assertEqual(codes, ["image-no-cell"])

    def test_no_sheet_at_all_is_an_error(self):
        doc = "## [Icons](icons)\n---\nicons\nCell: 64\n---\n\n" \
              "### [Job](wanted)\n---\nAt: 0, 0\n---\n"
        records = images_from_section(self.section(doc, "icons"))
        codes = [c for _k, _s, c, _m in images_validate(records)]
        self.assertEqual(codes, ["image-no-sheet"])

    def test_a_cell_off_the_edge_of_the_sheet_is_a_warning(self):
        """The one an author hits most: a sheet grew a row in their head, not on disk."""
        records = images_from_section(self.section(ICONS, "icons"))
        real = ImageAtlas.is_valid
        size = ImageAtlas.get_size
        ImageAtlas.is_valid = lambda self: True
        ImageAtlas.get_size = lambda self: (128, 128)      # a 2x2 sheet of 64px cells
        try:
            problems = {k: c for k, _s, c, _m in images_validate(records)}
        finally:
            ImageAtlas.is_valid = real
            ImageAtlas.get_size = size
        self.assertNotIn("wanted", problems)               # At: 0,0 fits
        self.assertEqual(problems.get("talks"), "image-off-sheet")   # At: 1,2 does not


class TheLinterFindsThemOnDisk(unittest.TestCase):
    """The runtime resolves art through the engine's mission paths, which `sbs lint` does
    not have - so the linter looks where the author would have put it, rooted at the file
    it was handed. Without this the pass would call every sheet in every mission missing."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "media", "icons"))
        with open(os.path.join(self.dir, "story.json"), "w") as f:
            f.write("{}")
        # A PNG header is all the linter reads: 16 bytes, then width and height.
        with open(os.path.join(self.dir, "media", "icons", "sheet.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">LL", 128, 128))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def lint(self, body):
        path = os.path.join(self.dir, "icons.amd")
        with open(path, "w") as f:
            f.write("# [Pack](pack)\n---\nUniverse\n---\n\n"
                    "## [Icons](icons)\n---\nicons\nSheet: icons/sheet\nCell: 64\n---\n\n"
                    + body)
        return {f.code: f for f in amd_lint(file_path=path)}

    def test_a_cell_that_exists_is_quiet(self):
        self.assertEqual(self.lint("### [Job](wanted)\n---\nAt: 0, 0\n---\n"), {})

    def test_a_cell_off_the_sheet_is_reported_with_its_line(self):
        found = self.lint("### [Job](wanted)\n---\nAt: 5, 5\n---\n")
        self.assertIn("image-off-sheet", found)
        self.assertEqual(found["image-off-sheet"].line, 13)      # the entry's heading

    def test_a_missing_sheet_is_an_error(self):
        found = self.lint("### [Job](wanted)\n---\nSheet: icons/nope\nAt: 0, 0\n---\n")
        self.assertIn("image-missing-file", found)
        self.assertTrue(found["image-missing-file"].is_error())

    def test_a_file_outside_any_mission_reports_only_what_it_knows(self):
        """No `story.json` above it means no mission root, so the file checks cannot run -
        and reporting every sheet as missing would be worse than saying nothing."""
        import tempfile
        loose = os.path.join(tempfile.mkdtemp(), "icons.amd")
        with open(loose, "w") as f:
            f.write("# [Pack](pack)\n---\nUniverse\n---\n\n"
                    "## [Icons](icons)\n---\nicons\nSheet: icons/sheet\nCell: 64\n---\n\n"
                    "### [Job](wanted)\n---\nAt: 0, 0\n---\n")
        codes = [f.code for f in amd_lint(file_path=loose)]
        self.assertNotIn("image-missing-file", codes)


if __name__ == "__main__":
    unittest.main()
