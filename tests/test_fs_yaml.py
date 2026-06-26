"""save_yaml_data round-trip. The fallback path used to call
yaml.safe_dump_all(f, data) (args reversed, multi-doc variant), which wrote an
empty/garbage file; this pins that it now writes a loadable single document."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import tempfile
import unittest

from sbs_utils.fs import save_yaml_data, load_yaml_data


class TestSaveYamlData(unittest.TestCase):
    def test_round_trip(self):
        data = {"START_TEXT": "Victory", "difficulty": 5,
                "stats": {"kralien_ships_destroyed": 3, "ships_surrender": 1},
                "players": ["Artemis", "Intrepid"]}
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        try:
            save_yaml_data(path, data)
            self.assertGreater(os.path.getsize(path), 0)   # actually wrote something
            back = load_yaml_data(path)
            self.assertEqual(back, data)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
