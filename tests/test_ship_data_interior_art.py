"""A hull that declares an interior must ship the sprite the engine cuts it from.

WHY THIS EXISTS. The engine does not take interior cell validity from shipData. It cuts
it from the alpha channel of ``<artfileroot>1024.png`` (GRID_REFERENCE.md s2). So a hull
can have a floor plan that parses, merges and resolves, correct ``internalmapw`` and
``internalmaph``, and still render a BLANK Engineering console - because the engine found
no valid cells to place any of it in.

Nothing else catches that:

* the floor plan parses and merges, so ``grid_get_layout`` answers;
* ``grid_rebuild_grid_objects`` spawns every object without complaint;
* the MOCK builds a hull map from ``internalmapw`` alone and never looks at the art, so
  every headless run reports a healthy grid;
* and ``_art_root_exists`` passes, because it matches the base name before the first dot -
  a bare ``<name>.obj`` satisfies it.

Found on Cosmos-TNG-Mod, where 36 of 51 hulls shipped no derived art: the pack relied on
the engine generating it in place, and the engine crashes doing that from a bare ``.obj``,
so it stopped partway. Reported as "the engineering grid does not work".
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import unittest
import tempfile

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  - settles the comms import order
from sbs_utils import fs
from sbs_utils.procedural import ship_data as sd


def _entry(key, root, interior=True):
    inner = f'"internalmapw": 10, "internalmaph": 12,' if interior else ""
    return f'{{"key": "{key}", "artfileroot": "{root}", {inner} "side": "tsn"}}'


def _doc(*entries):
    return '{"#ship-list": [' + ",".join(entries) + ']}\n'


class TestInteriorArtCheck(unittest.TestCase):
    """The check itself, against a synthetic install so it runs anywhere."""

    def setUp(self):
        self._saved = fs.exe_dir
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ships = os.path.join(self.root, "data", "graphics", "ships")
        os.makedirs(self.ships)
        fs.exe_dir = self.root

    def tearDown(self):
        fs.exe_dir = self._saved
        self._tmp.cleanup()

    def _put(self, *names):
        for n in names:
            with open(os.path.join(self.ships, n), "wb") as f:
                f.write(b"x")

    def test_complete_art_is_quiet(self):
        self._put("good.obj", "good1024.png", "good256.png")
        self.assertEqual(
            sd._interior_art_that_is_not_there(_doc(_entry("good", "ships/good"))), [])

    def test_missing_sprites_are_reported(self):
        # The exact TNG shape: geometry present, derived art never generated.
        self._put("bare.obj")
        found = sd._interior_art_that_is_not_there(_doc(_entry("bare", "ships/bare")))
        self.assertEqual(len(found), 1)
        key, root, absent = found[0]
        self.assertEqual(key, "bare")
        self.assertEqual(sorted(absent), ["1024.png", "256.png"])

    def test_half_baked_pack_is_reported(self):
        # One sprite without the other is half-generated, not a configuration choice.
        self._put("half.obj", "half1024.png")
        found = sd._interior_art_that_is_not_there(_doc(_entry("half", "ships/half")))
        self.assertEqual([a for _, _, a in found], [["256.png"]])

    def test_a_hull_with_no_interior_is_not_asked_for_a_sprite(self):
        self._put("nogrid.obj")
        self.assertEqual(
            sd._interior_art_that_is_not_there(
                _doc(_entry("nogrid", "ships/nogrid", interior=False))), [])

    def test_the_old_art_check_still_passes_on_a_bare_obj(self):
        # The reason this had to be a SEPARATE check rather than a stricter one: the
        # family match is satisfied by geometry alone.
        self._put("bare.obj")
        self.assertEqual(sd._art_that_is_not_there(_doc(_entry("bare", "ships/bare"))), [])

    def test_quiet_when_it_cannot_check(self):
        # No install to compare against - a check that failed everything on a CI runner
        # would be worse than no check.
        fs.exe_dir = os.path.join(self.root, "nope")
        self._put("bare.obj")
        self.assertEqual(
            sd._interior_art_that_is_not_there(_doc(_entry("bare", "ships/bare"))), [])

    def test_junk_never_raises(self):
        for bad in ("", "not yaml: [", '{"#ship-list": "nope"}', '{"#ship-list": [1, 2]}'):
            self.assertEqual(sd._interior_art_that_is_not_there(bad), [])


class TestStockCorpusHasItsSprites(unittest.TestCase):
    """Every stock hull that declares an interior has the sprite. Skipped without art."""

    def test_stock_hulls(self):
        graphics = os.path.join(fs.get_artemis_dir(), "data", "graphics")
        shipdata = os.path.join(fs.get_artemis_dir(), "data", "shipData.yaml")
        if not os.path.isdir(graphics) or not os.path.isfile(shipdata):
            self.skipTest("no Artemis install to check against")
        with open(shipdata, encoding="utf-8", errors="replace") as f:
            missing = sd._interior_art_that_is_not_there(f.read())
        self.assertEqual(
            missing, [],
            "stock hulls declaring an interior with no silhouette sprite: "
            + ", ".join(k for k, _, _ in missing))


class TestMockSaysSoEvenThoughItCannotReproduce(unittest.TestCase):
    """The mock stays permissive about a missing mask, but must not stay SILENT.

    ``open_cells`` deliberately reads a missing mask as "unknown" and leaves every cell
    open - a base-resolution change must never silently delete every hull's interior.
    The cost of that choice is that the mock shows a full grid for exactly the hulls the
    engine draws blank, so the warning is the only headless signal there is.
    """

    def setUp(self):
        from cosmos_dev.mock import hull_mask
        self.hm = hull_mask
        hull_mask.clear_cache()

    def tearDown(self):
        self.hm.clear_cache()

    def test_warns_once_per_hull(self):
        root = "ships/definitely_not_a_real_hull_xyzzy"
        self.assertTrue(self.hm.mask_is_missing(root))
        self.assertTrue(self.hm.warn_once_if_mask_missing(root, "xyzzy"))
        self.assertFalse(self.hm.warn_once_if_mask_missing(root, "xyzzy"),
                         "a hull must be reported once, not once per hull-map build")
        self.assertIn("xyzzy", self.hm.warned_no_mask())

    def test_silent_when_the_mask_is_there(self):
        # A stock hull that really does have its sprite.
        self.assertFalse(self.hm.mask_is_missing("ships/tsn_light_cruiser"))
        self.assertFalse(
            self.hm.warn_once_if_mask_missing("ships/tsn_light_cruiser", "tsn_light_cruiser"))

    def test_cleared_for_the_next_mission(self):
        self.hm.warn_once_if_mask_missing("ships/nope_xyzzy", "xyzzy")
        self.hm.clear_cache()
        self.assertEqual(self.hm.warned_no_mask(), set(),
                         "run 2 deserves its own warning")


if __name__ == "__main__":
    unittest.main()
