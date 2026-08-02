"""The shared Library: one tab, many sources.

Codex and Library were the same idea twice - same renderer, different hard-coded file.
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_doc
from sbs_utils.procedural.amd_doc import (lore_register, lore_sources, lore_clear,
                                          lore_available, lore_document,
                                          amd_has_content, _read_from_addon)

LM_LORE = """# [Galactic Helpfile](zunok)

## [Races](races)

### [Arvonians](arvonians)

Snobs.
"""

UNIVERSE_LORE = """# [Codex](codex)

## [Systems](systems)

### [The Veilfall](veilfall)

A red belt.
"""


class LoreBase(unittest.TestCase):
    def setUp(self):
        lore_clear()
        self.dir = tempfile.mkdtemp()
        self._files = {}
        # Resolve through a stub so the test never depends on a mission layout.
        self._real = amd_doc.amd_read_content
        amd_doc.amd_read_content = lambda f: self._files.get(f)
        self._real_has = amd_doc.amd_has_content
        amd_doc.amd_has_content = lambda f: self._files.get(f) is not None

    def tearDown(self):
        amd_doc.amd_read_content = self._real
        amd_doc.amd_has_content = self._real_has
        lore_clear()


class TestLoreRegistry(LoreBase):
    def test_nothing_registered_means_no_library(self):
        self.assertFalse(lore_available())
        self.assertEqual(lore_document()["children"], [])

    def test_a_source_whose_file_is_missing_does_not_conjure_a_tab(self):
        lore_register("lm", "Galactic Helpfile", "library_docs.amd")
        self.assertFalse(lore_available())

    def test_one_source(self):
        self._files["library_docs.amd"] = LM_LORE
        lore_register("lm", "Galactic Helpfile", "library_docs.amd")
        self.assertTrue(lore_available())
        kids = lore_document()["children"]
        self.assertEqual(len(kids), 1)
        self.assertEqual(kids[0]["display_text"], "Galactic Helpfile")

    def test_two_sources_merge_into_one_book(self):
        self._files["library_docs.amd"] = LM_LORE
        self._files["lore.amd"] = UNIVERSE_LORE
        lore_register("lm", "Galactic Helpfile", "library_docs.amd")
        lore_register("universe", "Codex", "lore.amd")
        kids = lore_document()["children"]
        self.assertEqual([k["display_text"] for k in kids],
                         ["Galactic Helpfile", "Codex"])

    def test_a_missing_source_is_skipped_not_fatal(self):
        self._files["lore.amd"] = UNIVERSE_LORE
        lore_register("lm", "Galactic Helpfile", "library_docs.amd")   # missing
        lore_register("universe", "Codex", "lore.amd")
        kids = lore_document()["children"]
        self.assertEqual([k["display_text"] for k in kids], ["Codex"])

    def test_registering_a_key_twice_replaces_it(self):
        """So a mission can substitute a library's section with its own file."""
        self._files["library_docs.amd"] = LM_LORE
        self._files["mine.amd"] = UNIVERSE_LORE
        lore_register("lm", "Galactic Helpfile", "library_docs.amd")
        lore_register("lm", "Our Own Lore", "mine.amd")
        self.assertEqual(len(lore_sources()), 1)
        kids = lore_document()["children"]
        self.assertEqual([k["display_text"] for k in kids], ["Our Own Lore"])

    def test_resolution_is_late(self):
        """Registered before the file exists; found once it does."""
        lore_register("lm", "Galactic Helpfile", "library_docs.amd")
        self.assertFalse(lore_available())
        self._files["library_docs.amd"] = LM_LORE
        self.assertTrue(lore_available())


class TestReadFromAddon(unittest.TestCase):
    """Step 3 of amd_read_content: a content-only addon a renderer does not live in."""

    def test_reads_from_a_folder(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "lore.amd"), "w") as f:
            f.write(LM_LORE)
        self.assertIn("Galactic Helpfile", _read_from_addon(d, "lore.amd"))

    def test_reads_from_a_zip(self):
        import zipfile
        d = tempfile.mkdtemp()
        z = os.path.join(d, "a.b.lore.v1.mastlib")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("lore.amd", LM_LORE)
            zf.writestr("sub/deep.amd", UNIVERSE_LORE)
        self.assertIn("Galactic Helpfile", _read_from_addon(z, "lore.amd"))
        self.assertIn("Codex", _read_from_addon(z, "sub/deep.amd"))

    def test_missing_is_none_not_an_exception(self):
        self.assertIsNone(_read_from_addon(tempfile.mkdtemp(), "nope.amd"))
        self.assertIsNone(_read_from_addon("no/such/path.mastlib", "nope.amd"))


if __name__ == "__main__":
    unittest.main()


class TestTabOnlyWhenFillable(unittest.TestCase):
    """Registering a source whose file resolves nowhere must not conjure a tab.

    universe_core registers its Codex unconditionally, so every mission loading the
    universe ENGINE reaches lore_register - Storm's Beacon has no lore.amd and was given
    an empty Library.
    """

    def setUp(self):
        lore_clear()
        self.tabs = []
        from sbs_utils.procedural.gui import console_tab
        self._real = console_tab.gui_tab_add_top
        console_tab.gui_tab_add_top = lambda name: self.tabs.append(name)
        self._files = {}
        self._real_has = amd_doc.amd_has_content
        amd_doc.amd_has_content = lambda f: self._files.get(f) is not None

    def tearDown(self):
        from sbs_utils.procedural.gui import console_tab
        console_tab.gui_tab_add_top = self._real
        amd_doc.amd_has_content = self._real_has
        lore_clear()

    def test_an_unresolvable_source_adds_no_tab(self):
        lore_register("universe", "Codex", "lore.amd")
        self.assertEqual(self.tabs, [])
        self.assertEqual(len(lore_sources()), 1, "the source should still be registered")

    def test_a_resolvable_source_adds_the_tab(self):
        self._files["lore.amd"] = "# [Codex](codex)\n"
        lore_register("universe", "Codex", "lore.amd")
        self.assertEqual(self.tabs, ["library"])

    def test_one_resolvable_source_among_several_is_enough(self):
        self._files["library_docs.amd"] = "# [Helpfile](zunok)\n"
        lore_register("universe", "Codex", "lore.amd")          # missing
        lore_register("lm", "Helpfile", "library_docs.amd")     # present
        self.assertEqual(self.tabs, ["library"])
