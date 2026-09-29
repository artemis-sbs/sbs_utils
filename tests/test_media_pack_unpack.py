"""A pinned media pack the CLI did not unpack is unpacked by the mission itself.

`sbs.pyz` unpacks only zips NAMED like a media pack (`<owner>.<repo>.media.<tag>.zip`),
and older copies of it are still out there. A pack from a repo that releases several -
`artemis-sbs.Cosmos-Tiles.frontier.v0.1.0.zip` - is not named that way, so without this
its art would silently not exist on a player's machine.
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

PACK = "artemis-sbs.Cosmos-Tiles.frontier.v0.1.0"


class TestPinnedPackUnpack(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.mission = os.path.join(self.root, "Mission")
        self.lib = os.path.join(self.root, "__lib__")
        os.makedirs(self.mission)
        os.makedirs(self.lib)
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump({"shared_media": [PACK + ".zip"]}, f)
        with zipfile.ZipFile(os.path.join(self.lib, PACK + ".zip"), "w") as z:
            z.writestr("tileart/frontier/manifest.json", "{}")
        old = fs.script_dir
        fs.script_dir = self.mission
        self.addCleanup(setattr, fs, "script_dir", old)
        MP._LIB_MEDIA = MP._MISSION = None
        self.addCleanup(setattr, MP, "_LIB_MEDIA", None)

    def test_A_PINNED_ZIP_IS_UNPACKED_AT_LOAD(self):
        roots = MP.media_roots()
        dest = os.path.join(self.lib, "media", PACK)
        self.assertIn(dest, roots)
        self.assertTrue(os.path.isfile(os.path.join(dest, "tileart", "frontier",
                                                    "manifest.json")))
        self.assertTrue(MP.media_shared_exists("tileart/frontier"))

    def test_an_unpacked_pack_is_left_alone(self):
        dest = os.path.join(self.lib, "media", PACK)
        os.makedirs(dest)
        MP.media_roots()
        self.assertEqual(os.listdir(dest), [])            # not re-extracted over

    def test_a_pack_that_is_not_there_is_not_an_error(self):
        os.remove(os.path.join(self.lib, PACK + ".zip"))
        MP.media_roots()
        self.assertFalse(os.path.isdir(os.path.join(self.lib, "media", PACK)))


if __name__ == "__main__":
    unittest.main()
