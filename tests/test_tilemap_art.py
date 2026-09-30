"""Art sets: logical sprite keys, drawn by whichever sets a mission loads.

* **Sets overlay key by key** - a pack that redraws only the people is a valid pack.
* **A set that is not there is said once and skipped** - the mission keeps its own art.
* **Sheets are found next to the manifest** - never through a versioned pack path.
* **Art dresses a tileset's kinds, never its rules** - walk and see stay the mission's.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import os
import shutil
import tempfile
import unittest

from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import tilemap_art as TA
from sbs_utils.procedural.gui.image import ImageAtlas


BUILTIN = {
    "sheets": {"all": "all.png"},
    "sprites": {
        "ta:crew": {"sheet": "all", "rect": [0, 0, 64, 64]},
        "ta:crate": {"sheet": "all", "rect": [64, 0, 128, 64]},
        "ta:dust": {"sheet": "all", "rect": [128, 0, 192, 64]},
        "ta:cart": {"sheet": "all", "rect": [192, 0, 320, 64], "base": [-1.3, -0.3, 1.3, 0.3]},
    },
    "ground": {"dust": {"cell": "ta:dust"}},
}

FANCY = {
    "sheets": {"chars": "chars.png", "ground": "ground"},
    "sprites": {
        "ta:crew": {"sheet": "chars", "rect": [0, 0, 128, 192], "cells": [1, 1.5]},
        "ta:crew_e_a": {"sheet": "chars", "rect": [128, 0, 256, 192], "cells": [1, 1.5]},
        "ta:dust_v2": {"sheet": "ground", "rect": [128, 0, 256, 128]},
        "ta:rock_we": {"sheet": "ground", "rect": [256, 0, 384, 128]},
        "ta:cart": {"sheet": "chars", "rect": [256, 0, 384, 128]},
        "ta:taxi": {"sheet": "chars", "rect": [384, 0, 768, 256], "cells": [3, 2],
                    "base": [-1.6, -0.55, 1.6, 0.55]},
    },
    "ground": {"dust": {"variants": ["ta:dust_v2"]},
               "rock": {"cell": "ta:rock_we", "tall": True, "walk": True},
               "lava": {"cell": "ta:dust"}},
}


class ArtBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.folders = {}
        for name, manifest in (("builtin", BUILTIN), ("fancy", FANCY)):
            folder = os.path.join(self.tmp, name)
            os.makedirs(folder)
            with open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            self.folders[name] = folder.replace("\\", "/")
        real_find = TA.tilemap_art_find
        TA.tilemap_art_find = lambda name: self.folders.get(name)
        self.addCleanup(setattr, TA, "tilemap_art_find", real_find)
        TA.tilemap_art_clear()
        self.addCleanup(TA.tilemap_art_clear)
        T.tilemap_clear_tilesets()
        self.addCleanup(T.tilemap_clear_tilesets)
        T.tilemap_tileset("tt", {"dust": {"cell": "old:dust"},
                                 "rock": {"cell": "old:rock", "walk": False}})
        self.addCleanup(self._forget_keys)

    def _forget_keys(self):
        for k in [k for k in ImageAtlas.all if str(k).startswith("ta:")]:
            ImageAtlas.all.pop(k, None)


class TestOverlay(ArtBase):
    def test_a_later_set_wins_key_by_key(self):
        self.assertEqual(TA.tilemap_art_use("builtin", "fancy", tileset="tt"),
                         ["builtin", "fancy"])
        self.assertEqual(TA.tilemap_art_origin("ta:crew"), "fancy")
        self.assertEqual(TA.tilemap_art_origin("ta:crate"), "builtin")
        self.assertEqual(ImageAtlas.all["ta:crew"].right, 128)
        self.assertEqual(TA.tilemap_sprite_footprint("ta:crew"), (1.0, 1.5, 0.5, 1.0))
        self.assertEqual(TA.tilemap_sprite_footprint("ta:crate"), TA.DEFAULT_FOOTPRINT)

    def test_A_MISSING_SET_IS_SKIPPED_AND_THE_MISSION_KEEPS_ITS_ART(self):
        loaded = TA.tilemap_art_use("builtin", "nowhere", tileset="tt")
        self.assertEqual(loaded, ["builtin"])
        self.assertIn("ta:crate", ImageAtlas.all)
        # Said once, not on every load.
        self.assertIn("nowhere", TA._WARNED)

    def test_CLEAR_TAKES_A_PACKS_KEYS_OUT_OF_THE_ATLAS(self):
        """The dev runner reuses one interpreter: a pack's facing frames left behind
        would be drawn in the next mission even if it never loads the pack."""
        TA.tilemap_art_use("builtin", "fancy")
        self.assertIn("ta:crew_e_a", ImageAtlas.all)
        TA.tilemap_art_clear()
        self.assertNotIn("ta:crew_e_a", ImageAtlas.all)

    def test_sheets_are_found_next_to_the_manifest(self):
        TA.tilemap_art_use("builtin", "fancy")
        self.assertIn("fancy/chars", ImageAtlas.all["ta:crew"].file.replace("\\", "/"))
        self.assertIn("builtin/all", ImageAtlas.all["ta:crate"].file.replace("\\", "/"))


class TestGround(ArtBase):
    def test_art_dresses_the_kinds_it_knows(self):
        TA.tilemap_art_use("builtin", "fancy", tileset="tt")
        dust = T._TILESETS["tt"]["dust"]
        self.assertEqual(dust["cell"], "ta:dust")
        self.assertEqual(dust["variants"], ["ta:dust", "ta:dust_v2"])
        rock = T._TILESETS["tt"]["rock"]
        self.assertEqual(rock["cell"], "ta:rock_we")
        self.assertTrue(rock["tall"])

    def test_A_KIND_CAN_WEAR_A_PACKS_GROUND_UNDER_ITS_OWN_NAME(self):
        """A map says `dust`; a shared pack draws `dirt_arid`. `look` joins them, and
        two kinds may share one look."""
        T.tilemap_tileset("tt", {"dust": {"look": "rock"}, "gravel": {"look": "rock"},
                                 "rock": {"walk": False}})
        TA.tilemap_art_use("builtin", "fancy", tileset="tt")
        for kind in ("dust", "gravel", "rock"):
            self.assertEqual(T._TILESETS["tt"][kind]["cell"], "ta:rock_we", kind)

    def test_ART_NEVER_CHANGES_THE_RULES(self):
        TA.tilemap_art_use("builtin", "fancy", tileset="tt")
        self.assertFalse(T._TILESETS["tt"]["rock"]["walk"])     # the manifest said walk
        self.assertNotIn("lava", T._TILESETS["tt"])              # nor adds kinds


class TestBase(ArtBase):
    """A big thing's GROUND - what it blocks - is its own field, never guessed from the
    picture, which is taller than the thing and carries its shadow."""

    def cells(self, rect):
        TA.tilemap_sprite_base("ta:probe", rect)
        return sorted(TA.tilemap_sprite_cells("ta:probe"))

    def test_no_base_is_one_cell(self):
        self.assertEqual(sorted(TA.tilemap_sprite_cells("ta:nothing")), [(0, 0)])

    def test_a_car_covers_three_cells_nose_to_tail(self):
        self.assertEqual(self.cells((-1.6, -0.55, 1.6, 0.55)), [(-1, 0), (0, 0), (1, 0)])

    def test_ONLY_A_CELL_MOSTLY_UNDER_IT_IS_COVERED(self):
        """A bunk 1.5 tiles long overhangs its neighbours by a quarter each: one cell. Two
        tiles long reaches exactly HALF way into each: still one."""
        self.assertEqual(self.cells((-0.77, -0.4, 0.77, 0.4)), [(0, 0)])
        self.assertEqual(self.cells((-1.0, -0.4, 1.0, 0.4)), [(0, 0)])
        self.assertEqual(self.cells((-1.2, -0.4, 1.2, 0.4)), [(-1, 0), (0, 0), (1, 0)])

    def test_a_barn_covers_its_whole_floor(self):
        got = self.cells((-3.4, -2.4, 3.4, 2.4))
        self.assertEqual(len(got), 7 * 5)
        self.assertIn((-3, -2), got)
        self.assertIn((3, 2), got)

    def test_ground_off_to_one_side_still_holds_its_own_cell(self):
        self.assertEqual(self.cells((0.2, -0.3, 1.8, 0.3)), [(0, 0), (1, 0)])

    def test_the_manifest_carries_it_and_a_later_look_owns_the_key(self):
        TA.tilemap_art_use("builtin")
        self.assertEqual(len(TA.tilemap_sprite_cells("ta:cart")), 3)
        TA.tilemap_art_use("builtin", "fancy")
        # fancy redraws the cart with no base: its ground went with the old picture.
        self.assertEqual(sorted(TA.tilemap_sprite_cells("ta:cart")), [(0, 0)])
        self.assertEqual(len(TA.tilemap_sprite_cells("ta:taxi")), 3)

    def test_clear_forgets_it(self):
        TA.tilemap_art_use("builtin", "fancy")
        TA.tilemap_art_clear()
        self.assertEqual(sorted(TA.tilemap_sprite_cells("ta:taxi")), [(0, 0)])


WALKER = {
    "sheets": {"chars": "chars.png"},
    "sprites": {
        "ta:guy_s_idle": {"sheet": "chars", "rect": [0, 0, 64, 96], "cells": [1, 1.5]},
        "ta:guy_e_idle": {"sheet": "chars", "rect": [64, 0, 128, 96], "cells": [1, 1.5],
                          "anchor": [0.3, 1.0], "base": [-0.2, -0.1, 0.4, 0.1]},
        "ta:guy_e_a": {"sheet": "chars", "rect": [128, 0, 192, 96], "cells": [1, 1.5]},
        "ta:sign_e": {"sheet": "chars", "rect": [192, 0, 256, 64]},
        "ta:tree": {"sheet": "chars", "rect": [256, 0, 384, 192], "mirror": True},
    },
}
DRAWN_WEST = {"sheets": {"c": "c2.png"},
              "sprites": {"ta:guy_w_idle": {"sheet": "c", "rect": [0, 0, 64, 96]}}}
NEW_EAST = {"sheets": {"c": "c3.png"},
            "sprites": {"ta:guy_e_idle": {"sheet": "c", "rect": [500, 0, 564, 96]},
                        "ta:tree": {"sheet": "c", "rect": [600, 0, 700, 100]}}}


class TestMirroring(ArtBase):
    """The engine draws a cell backwards when its rect runs backwards, so a set need only
    draw one side of a figure, and a prop can have a mirrored twin for variety."""

    def setUp(self):
        super().setUp()
        for name, manifest in (("walker", WALKER), ("drawnwest", DRAWN_WEST),
                               ("neweast", NEW_EAST)):
            folder = os.path.join(self.tmp, name)
            os.makedirs(folder)
            with open(os.path.join(folder, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            self.folders[name] = folder.replace("\\", "/")

    def rect(self, key):
        a = ImageAtlas.all[key]
        return (a.left, a.top, a.right, a.bottom)

    def test_A_FIGURE_GETS_THE_SIDE_IT_LACKS(self):
        TA.tilemap_art_use("walker")
        self.assertEqual(self.rect("ta:guy_w_idle"), (128, 0, 64, 96))
        self.assertEqual(self.rect("ta:guy_w_a"), (192, 0, 128, 96))
        # Its feet stay on the cell, and the ground it covers flips too.
        self.assertEqual(TA.tilemap_sprite_footprint("ta:guy_w_idle"), (1.0, 1.5, 0.7, 1.0))
        self.assertEqual(TA._BASES["ta:guy_w_idle"], (-0.4, -0.1, 0.2, 0.1))
        self.assertEqual(TA.tilemap_art_origin("ta:guy_w_idle"), "walker (mirrored)")

    def test_only_a_figure_is_given_a_side(self):
        TA.tilemap_art_use("walker")
        self.assertNotIn("ta:sign_w", ImageAtlas.all)

    def test_A_WEST_A_SET_DREW_IS_KEPT_WHICHEVER_LOADS_FIRST(self):
        for order in (("walker", "drawnwest"), ("drawnwest", "walker")):
            TA.tilemap_art_clear()
            TA.tilemap_art_use(*order)
            self.assertEqual(self.rect("ta:guy_w_idle"), (0, 0, 64, 96), order)
            self.assertEqual(TA.tilemap_art_origin("ta:guy_w_idle"), "drawnwest")

    def test_a_later_east_takes_its_west_with_it(self):
        TA.tilemap_art_use("walker", "neweast")
        self.assertEqual(self.rect("ta:guy_w_idle"), (564, 0, 500, 96))

    def test_mirror_true_gives_a_prop_a_twin(self):
        TA.tilemap_art_use("walker")
        self.assertEqual(TA.tilemap_sprite_twin("ta:tree"), "ta:tree_mirror")
        self.assertEqual(self.rect("ta:tree_mirror"), (384, 0, 256, 192))
        self.assertIsNone(TA.tilemap_sprite_twin("ta:sign_e"))

    def test_A_TREE_REDRAWN_WITHOUT_MIRROR_LOSES_ITS_OLD_TWIN(self):
        TA.tilemap_art_use("walker", "neweast")
        self.assertIsNone(TA.tilemap_sprite_twin("ta:tree"))
        self.assertNotIn("ta:tree_mirror", ImageAtlas.all)

    def test_clear_takes_the_derived_looks_out(self):
        TA.tilemap_art_use("walker")
        TA.tilemap_art_clear()
        for key in ("ta:guy_w_idle", "ta:tree_mirror"):
            self.assertNotIn(key, ImageAtlas.all)


class TestSetsFromSettings(unittest.TestCase):
    def test_builtin_always_comes_first(self):
        self.assertEqual(TA.tilemap_art_sets("synty, extra")[:1], ["builtin"])

    def test_a_comma_string_or_a_list(self):
        from sbs_utils.procedural import settings as S
        real = S.settings_get_defaults
        S.settings_get_defaults = lambda: {"TILE_ART": "synty, extra"}
        self.addCleanup(setattr, S, "settings_get_defaults", real)
        self.assertEqual(TA.tilemap_art_sets(), ["builtin", "synty", "extra"])
        S.settings_get_defaults = lambda: {"TILE_ART": ["synty"]}
        self.assertEqual(TA.tilemap_art_sets(), ["builtin", "synty"])


if __name__ == "__main__":
    unittest.main()
