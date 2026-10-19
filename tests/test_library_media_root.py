"""The library's own media pack is a root no mission has to declare.

Art the LIBRARY needs (xESS icons, the EVA suit, ship portraits) used to live in
LegendaryMissions' pack, so a mission that did not pin LM lost it silently. The pack is
now derived from the sbs_utils sbslib the mission pins, and it resolves LAST: the
mission's own art and any pack it pinned still win.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import os
import shutil
import tempfile
import unittest
import zipfile

import sbs_utils.fs as fs
from sbs_utils.procedural import media_paths as MP
from sbs_utils.procedural import amd_assets

SBSLIB = "artemis-sbs.sbs_utils.v1.4.0.sbslib"
LIBPACK = "artemis-sbs.sbs_utils.media.v1.4.0"
LMPACK = "artemis-sbs.LegendaryMissions.media.v1.4.0"


class TestLibraryMediaPackName(unittest.TestCase):
    def test_derived_from_the_sbslib_pin(self):
        self.assertEqual(MP.library_media_pack([SBSLIB]), LIBPACK)
        self.assertEqual(MP.library_media_pack(SBSLIB), LIBPACK)

    def test_other_libraries_and_nothing_give_none(self):
        self.assertIsNone(MP.library_media_pack(["artemis-sbs.cosmos_dev.v1.4.0.sbslib"]))
        self.assertIsNone(MP.library_media_pack(None))
        self.assertIsNone(MP.library_media_pack([]))


class TestLibraryMediaRoot(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.mission = os.path.join(self.root, "Mission")
        self.lib = os.path.join(self.root, "__lib__")
        os.makedirs(os.path.join(self.mission, "media"))
        os.makedirs(self.lib)
        old = fs.script_dir
        fs.script_dir = self.mission
        self.addCleanup(setattr, fs, "script_dir", old)
        # Pretend the library is PACKAGED: the working tree's media/ must not answer.
        real = MP._library_tree_media
        MP._library_tree_media = lambda: None
        self.addCleanup(setattr, MP, "_library_tree_media", real)
        MP._LIB_MEDIA = MP._MISSION = None
        self.addCleanup(setattr, MP, "_LIB_MEDIA", None)

    def _story(self, **data):
        data.setdefault("sbslib", [SBSLIB])
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump(data, f)

    def _pack(self, name, files):
        with zipfile.ZipFile(os.path.join(self.lib, name + ".zip"), "w") as z:
            for f in files:
                z.writestr(f, "x")

    def test_UNDECLARED_library_pack_resolves(self):
        self._story()
        self._pack(LIBPACK, ["epadd/icons.png"])
        roots = MP.media_roots()
        self.assertEqual(roots[-1], os.path.join(self.lib, "media", LIBPACK))
        self.assertTrue(MP.media_shared_exists("epadd/icons"))
        self.assertIn(LIBPACK, MP.media_shared("epadd/icons"))

    def test_library_is_LAST_so_a_pinned_pack_wins(self):
        self._story(shared_media=[LMPACK + ".zip"])
        self._pack(LIBPACK, ["casino/terran_deck.png"])
        self._pack(LMPACK, ["casino/terran_deck.png"])
        self.assertIn(LMPACK, MP.media_shared("casino/terran_deck"))

    def test_mission_art_wins_over_the_library(self):
        self._story()
        self._pack(LIBPACK, ["casino/terran_deck.png"])
        os.makedirs(os.path.join(self.mission, "media", "casino"))
        open(os.path.join(self.mission, "media", "casino", "terran_deck.png"), "w").close()
        self.assertEqual(MP.media_shared("casino/terran_deck"), "media/casino/terran_deck")

    def test_no_sbslib_pin_no_library_root(self):
        self._story(sbslib=[])
        self.assertEqual(MP.media_roots(), [os.path.join(self.mission, "media")])

    def test_missing_pack_is_not_an_error(self):
        self._story()
        self.assertEqual(MP.media_roots(), [os.path.join(self.mission, "media")])

    def test_amd_assets_sees_the_library_pack(self):
        self._story()
        self._pack(LIBPACK, ["epadd/icons.png"])
        MP.media_roots()                                   # unpacks it
        roots = amd_assets.media_roots(self.mission)
        self.assertIn(os.path.join(self.lib, "media", LIBPACK), roots)


class TestWorkingTreeLibraryMedia(unittest.TestCase):
    def test_working_tree_media_is_the_library_root(self):
        """Running from source, art added to sbs_utils/media is seen before any sbs lib."""
        tree = MP._library_tree_media()
        import sbs_utils
        repo = os.path.dirname(os.path.dirname(os.path.abspath(sbs_utils.__file__)))
        if os.path.isdir(os.path.join(repo, "media")):
            self.assertEqual(tree, os.path.join(repo, "media"))
        else:
            self.assertIsNone(tree)


if __name__ == "__main__":
    unittest.main()
