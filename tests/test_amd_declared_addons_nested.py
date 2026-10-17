"""declared_addon_paths finds `__lib__` for a mission nested below data/missions.

A mission at `data/missions/_sandbox/x/y` declares its mastlibs by name; the zips are in
`data/missions/__lib__`, three folders up. Looking only one level up found nothing, so
every addon vocabulary went missing and lint warned "not a field a side has" on fields
the mission's own addons define.
"""
import json
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_vocab import declared_addon_paths


class TestDeclaredAddonsNested(unittest.TestCase):

    def _layout(self, tmp, *nest):
        lib = os.path.join(tmp, "data", "missions", "__lib__")
        os.makedirs(lib)
        zip_name = "artemis-sbs.OpenUniverse.ou.v1.4.0.mastlib"
        open(os.path.join(lib, zip_name), "wb").close()
        mission = os.path.join(tmp, "data", "missions", *nest)
        os.makedirs(mission)
        with open(os.path.join(mission, "story.json"), "w") as f:
            json.dump({"mastlib": [zip_name]}, f)
        return mission, os.path.join(lib, zip_name)

    def test_mission_directly_in_missions(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission, zip_path = self._layout(tmp, "MyUniverse")
            self.assertEqual(declared_addon_paths(mission), [zip_path])

    def test_mission_two_folders_below_missions(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission, zip_path = self._layout(tmp, "_sandbox", "x", "y")
            self.assertEqual(declared_addon_paths(mission), [zip_path])


if __name__ == "__main__":
    unittest.main()
