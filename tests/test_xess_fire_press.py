"""The Fire app's second press USES the target - read at press time, not at build time.

"Select the row, and press it again" (C4-08, C4-09). The first press aims; the second
uses. The handler compared the row with the aim captured when the screen was BUILT, and
nothing rebuilds the screen when the aim changes, so in the engine the second press only
aimed again: the slab was targeted (the red cross on the radar) and never cut (scouting,
2026-10-18).

    python -m unittest tests.test_xess_fire_press
"""
import unittest
from unittest import mock

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  import first to break a circular import
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural import eva_tools as T

CID = 0x8000000000000021


class FirePress(unittest.TestCase):
    def setUp(self):
        self.aim, self.used = None, []

        def aim(cid, key):
            self.aim = key
            return True

        def selected(cid):
            return self.aim

        def use(cid, key):
            self.used.append(key)
            return True

        self.patches = [mock.patch.object(T, "eva_aim", aim),
                        mock.patch.object(T, "eva_selected_target", selected),
                        mock.patch.object(T, "eva_use", use)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_first_press_aims_second_press_uses(self):
        self.assertEqual(X._fire_press(CID, "slab"), "aim")
        self.assertEqual(self.used, [])
        self.assertEqual(X._fire_press(CID, "slab"), "use")
        self.assertEqual(self.used, ["slab"])

    def test_pressing_another_row_moves_the_aim(self):
        X._fire_press(CID, "slab")
        self.assertEqual(X._fire_press(CID, "cache"), "aim")
        self.assertEqual(self.used, [])


if __name__ == "__main__":
    unittest.main()
