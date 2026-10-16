"""The editor's preview reports art sets the writer named and cannot find - never the
optional `builtin` set every mission is given first. A mission from the `away` template
has no `builtin` art, and the Tile Map Editor's footer read "(not found: builtin)" for it.

    python -m unittest tests.test_tilemap_preview_missing
"""
import os
import shutil
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import tilemap_preview as TP


class PreviewMissingSets(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.mission = os.path.join(self.root, "MyAway")
        os.makedirs(self.mission)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _missing(self, tile_art):
        with open(os.path.join(self.mission, "settings.yaml"), "w", encoding="utf-8") as fh:
            fh.write(f"TILE_ART: {tile_art}\n")
        names = TP.tilemap_preview_sets(self.mission)
        self.assertEqual(names[0], "builtin")
        return TP._load_sets(self.mission, names)[3]

    def test_builtin_is_never_reported_missing(self):
        self.assertNotIn("builtin", self._missing("nosuchset_a"))

    def test_a_named_set_that_is_not_there_is_reported(self):
        self.assertEqual(self._missing("nosuchset_a, nosuchset_b"), ["nosuchset_a", "nosuchset_b"])


if __name__ == "__main__":
    unittest.main()
