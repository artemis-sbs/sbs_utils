"""More quiet mistakes on the ground and at a universe's sites, made loud.

Found by the author course (Class 3, Lectures 8 to 12; Class 5, Lecture 10). Every one
was `clean` in lint and wrong in the game, and each is reported only where the game's
own reading leaves no doubt:

* two `.tiles` files saying the same `area:` (one is never loaded);
* a map drawn bigger than its `size:` line (the rest is cut off);
* an exit's arrival written without its `@`;
* a `Patrol:` whose points are split by commas (it is read as one point);
* `Site:` / `Site file:` naming a file that is not there;
* a site with no map and its rooms under `## [Scenes](scenes)` - no site at all;
* a site's `## Hails` with no answer that sends `; signal boarding_down`.

    python -m unittest tests.test_tilemap_lint_quiet
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import os
import shutil
import tempfile
import unittest
import zipfile

from sbs_utils.procedural import tilemap_lint as TL

TILESET = """tileset: test
kinds:
  dirt:  walk see
  rock:
"""

YARD = """area: yard
title: The Yard
tileset: test
entry: landing
legend:
  .: dirt
  #: rock
  L: dirt @landing
  g: dirt @to_gully
exits:
  to_gully: gully @gully_mouth
---
######
#.L.g#
#....#
######
"""

GULLY = """area: gully
title: Dry Gully
tileset: test
legend:
  .: dirt
  #: rock
  m: dirt @gully_mouth
---
#####
#m..#
#####
"""

WORLD = """# [Kesh Relay](mission)

## [People](people)

### [The Crawler](crawler)
---
Area: yard
At: 1, 1
Patrol: 1, 1; 3, 2; 4, 2
---
"""


class _Folder(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tile_quiet_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def put(self, name, text):
        path = os.path.join(self.root, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def mission(self):
        return [(rel.replace("\\", "/"), f) for rel, f in TL.tilemap_lint_mission(self.root)]


class TheMaps(_Folder):
    def setUp(self):
        super().setUp()
        self.put("ground/test.tileset", TILESET)
        self.put("ground/yard.tiles", YARD)
        self.put("ground/gully.tiles", GULLY)
        self.put("mission.amd", WORLD)

    def test_the_lessons_maps_are_clean(self):
        self.assertEqual(self.mission(), [])

    # -- two files, one area ------------------------------------------------------------
    def test_TWO_FILES_THAT_SAY_THE_SAME_AREA(self):
        """Class 3, Lecture 9: the new map saved with the old one's first line."""
        self.put("ground/cistern.tiles", GULLY)            # meant `area: cistern`
        got = [(rel, f) for rel, f in self.mission() if f.code == "tiles-duplicate-area"]
        self.assertEqual(len(got), 1)
        rel, f = got[0]
        self.assertEqual(rel, "ground/gully.tiles")         # the later name of the two
        self.assertEqual(f.line, 1)
        self.assertIn("`area: gully`", f.message)
        self.assertIn("cistern.tiles says the same", f.message)
        self.assertIn("never loaded", f.message)

    # -- size: ---------------------------------------------------------------------------
    def test_A_ROW_LONGER_THAN_SIZE(self):
        self.put("ground/yard.tiles", YARD.replace("tileset: test\n",
                                                   "tileset: test\nsize: 5x4\n"))
        got = [f for _rel, f in self.mission() if f.code == "tiles-size-cut"]
        self.assertEqual(len(got), 1)
        self.assertIn("6 cells wide and `size:` says 5", got[0].message)
        self.assertIn("(4 rows are too wide)", got[0].message)
        self.assertEqual(got[0].col, 5)

    def test_MORE_ROWS_THAN_SIZE(self):
        self.put("ground/yard.tiles", YARD.replace("tileset: test\n",
                                                   "tileset: test\nsize: 6x3\n"))
        got = [f for _rel, f in self.mission() if f.code == "tiles-size-cut"]
        self.assertEqual(len(got), 1)
        self.assertIn("`size:` says the map is 3 rows, and this is row 4", got[0].message)

    def test_a_size_that_fits_or_is_bigger_says_nothing(self):
        for size in ("6x4", "10x8"):
            with self.subTest(size=size):
                self.put("ground/yard.tiles", YARD.replace(
                    "tileset: test\n", f"tileset: test\nsize: {size}\n"))
                self.assertEqual([f for _r, f in self.mission()
                                  if f.code == "tiles-size-cut"], [])

    # -- exits ---------------------------------------------------------------------------
    def test_AN_ARRIVAL_WITH_NO_AT_SIGN(self):
        self.put("ground/yard.tiles", YARD.replace("gully @gully_mouth", "gully gully_mouth"))
        got = [f for _rel, f in self.mission() if f.code == "tiles-exit"]
        self.assertEqual(len(got), 1)
        self.assertIn("neither `@` and a mark's name nor x, y", got[0].message)
        self.assertIn("Write `gully @gully_mouth`", got[0].message)

    def test_an_arrival_that_is_a_cell_is_fine(self):
        self.put("ground/yard.tiles", YARD.replace("gully @gully_mouth", "gully 2, 1"))
        self.assertEqual([f for _rel, f in self.mission() if f.code == "tiles-exit"], [])

    # -- patrols -------------------------------------------------------------------------
    def test_A_PATROL_SPLIT_BY_COMMAS(self):
        """Class 3, Lecture 11: the crawler that never moves."""
        self.put("mission.amd", WORLD.replace("Patrol: 1, 1; 3, 2; 4, 2",
                                              "Patrol: 1, 1, 3, 2, 4, 2"))
        got = [f for _rel, f in self.mission() if f.code == "patrol-shape"]
        self.assertEqual(len(got), 1)
        self.assertIn("read as ONE point (1, 1)", got[0].message)
        self.assertIn("Write `Patrol: 1, 1; 3, 2; 4, 2`", got[0].message)

    def test_the_game_reads_it_as_one_point(self):
        """What the warning says, asked of the game's own reader."""
        from sbs_utils.procedural.boarding_combat import _cells
        self.assertEqual(_cells("1, 1, 3, 2, 4, 2"), [(1, 1)])
        self.assertEqual(_cells("1, 1; 3, 2; 4, 2"), [(1, 1), (3, 2), (4, 2)])

    def test_semicolons_and_two_spaces_are_both_fine(self):
        for patrol in ("1, 1; 3, 2; 4, 2", "1 1; 3 2", "1,1  3,2  4,2"):
            with self.subTest(patrol=patrol):
                self.put("mission.amd", WORLD.replace("1, 1; 3, 2; 4, 2", patrol))
                self.assertEqual([f for _r, f in self.mission()
                                  if f.code == "patrol-shape"], [])


# --- a universe's sites ----------------------------------------------------------------------

UNIVERSE = """# [The Kestrel Verge](kestrel_verge)

## [Landmarks](landmarks)

### [Customs House](customs_station)
---
At: 0, 0
Kind: station
Site: customs
---
A customs post.
"""

CUSTOMS = """# [The Customs House](customs_site)

## [Hails](hails)

### [The Call](customs_call)
---
Speaker: customs
When: hail
---
% Kestrel Customs. You are cleared to come aboard.
- [Assemble a boarding party]() ; signal boarding_down
- [Stay aboard]()

## [Scenes](boarding)

### [The Counter](customs_counter)
% A long counter, and a clerk behind it.
- [Read the manifest](customs_counter) ; learn manifest, signal manifest_read
- [Beam back up]()
"""


class TheSites(_Folder):
    def setUp(self):
        super().setUp()
        self.put("story.json", '{"mastlib": []}\n')
        self.put("kestrel_verge.amd", UNIVERSE)
        self.put("customs.amd", CUSTOMS)

    def sites(self):
        return [(os.path.relpath(path, self.root).replace("\\", "/"), f)
                for path, f in TL.tilemap_lint_sites(self.root)]

    def test_the_lessons_site_is_clean(self):
        self.assertEqual(self.sites(), [])

    # -- the file that is not there ----------------------------------------------------
    def test_A_SITE_WHOSE_FILE_IS_NOT_THERE(self):
        os.remove(os.path.join(self.root, "customs.amd"))
        got = self.sites()
        self.assertEqual([(rel, f.code, f.line) for rel, f in got],
                         [("kestrel_verge.amd", "site-file-missing", 9)])
        self.assertIn("`Site: customs` is looked for in `customs.amd`", got[0][1].message)
        self.assertIn("docking there does nothing", got[0][1].message)

    def test_A_SITE_FILE_LINE_NAMING_NO_FILE(self):
        self.put("kestrel_verge.amd", UNIVERSE.replace(
            "Site: customs\n", "Site: customs\nSite file: places/custom_house.amd\n"))
        got = self.sites()
        self.assertEqual([(rel, f.code, f.line) for rel, f in got],
                         [("kestrel_verge.amd", "site-file-missing", 10)])
        self.assertIn("names the file `places/custom_house.amd`", got[0][1].message)

    def test_a_file_the_universes_own_addon_carries_is_there(self):
        """The game looks beside the universe file, then in the addon it came from."""
        os.remove(os.path.join(self.root, "customs.amd"))
        lib = os.path.join(os.path.dirname(self.root), "__lib__")
        os.makedirs(lib, exist_ok=True)
        self.addCleanup(shutil.rmtree, lib, True)
        name = "owner.Repo.universe_core.v1.mastlib"
        with zipfile.ZipFile(os.path.join(lib, name), "w") as z:
            z.writestr("customs.amd", CUSTOMS)
        with open(os.path.join(self.root, "story.json"), "w") as f:
            json.dump({"mastlib": [name]}, f)
        self.assertEqual(self.sites(), [])

    # -- no rooms ------------------------------------------------------------------------
    def test_ROOMS_UNDER_SCENES_AND_NO_MAP_IS_NO_SITE(self):
        """Class 5, Lecture 10: a text site headed `## [Scenes](scenes)` - no call, no
        site, nothing in any log."""
        self.put("customs.amd", CUSTOMS.replace("## [Scenes](boarding)", "## [Scenes](scenes)"))
        got = self.sites()
        self.assertEqual([(rel, f.code) for rel, f in got], [("customs.amd", "site-no-rooms")])
        f = got[0][1]
        self.assertEqual(f.line, 14)                        # the chapter's heading
        self.assertIn("its rooms are under a chapter keyed `scenes`", f.message)
        self.assertIn("this site will not exist", f.message)
        self.assertIn("`## [Scenes](boarding)`", f.message)

    def test_no_rooms_at_all(self):
        self.put("customs.amd", CUSTOMS[:CUSTOMS.index("## [Scenes]")])
        got = self.sites()
        self.assertEqual([f.code for _rel, f in got], ["site-no-rooms"])
        self.assertIn("it has no rooms", got[0][1].message)

    def test_the_same_file_with_a_map_of_its_key_is_a_walked_site(self):
        self.put("customs.amd", CUSTOMS.replace("## [Scenes](boarding)", "## [Scenes](scenes)"))
        self.put("ground/test.tileset", TILESET)
        self.put("ground/customs.tiles", GULLY.replace("area: gully", "area: customs"))
        self.assertEqual(self.sites(), [])

    # -- the call ------------------------------------------------------------------------
    def test_A_CALL_NOBODY_CAN_ACCEPT(self):
        for bad in ("- [Assemble a boarding party]()",
                    "- [Assemble a boarding party]() ; signal boarding_dwn",
                    "- [Assemble a boarding party]() signal boarding_down"):
            with self.subTest(bad=bad):
                self.put("customs.amd", CUSTOMS.replace(
                    "- [Assemble a boarding party]() ; signal boarding_down", bad))
                got = self.sites()
                self.assertEqual([(rel, f.code, f.line) for rel, f in got],
                                 [("customs.amd", "site-hail-no-way-down", 3)])
                self.assertIn("can never go down", got[0][1].message)
                self.assertIn("; signal boarding_down", got[0][1].message)

    def test_the_games_own_check_agrees(self):
        """`universe_sites._universe_site_hail_sends` reads an answer the same way."""
        from sbs_utils.procedural.amd import amd_choice
        good = amd_choice("- [Assemble a boarding party]() ; signal boarding_down")
        self.assertEqual([list(o) for o in good["outcomes"]], [["signal", "boarding_down"]])

    def test_a_site_with_no_hails_chapter_is_offered_on_arrival(self):
        self.put("customs.amd", "# [The Customs House](customs_site)\n\n"
                 + CUSTOMS[CUSTOMS.index("## [Scenes]"):])
        self.assertEqual(self.sites(), [])


if __name__ == "__main__":
    unittest.main()
