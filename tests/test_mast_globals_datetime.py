"""datetime is exposed in the MAST eval namespace (used e.g. by LM's game-results
YAML save for a wall-clock timestamp). Purely additive - pin it so it isn't dropped."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from sbs_utils.mast.mast_globals import MastGlobals


class TestMastGlobalsDatetime(unittest.TestCase):
    def test_datetime_present_and_usable(self):
        g = MastGlobals.globals
        self.assertIn("datetime", g)
        stamp = eval('datetime.datetime.now().strftime("%Y")', dict(g), {})
        self.assertEqual(len(stamp), 4)   # a 4-digit year


if __name__ == "__main__":
    unittest.main()
