"""What the library's own media pack carries, and that library code finds it WITHOUT
LegendaryMissions.

The xESS asks for `epadd.*` icons and the EVA code for the `lm_eva_suit` hull. Both used
to exist only when a mission pinned LM's pack. They now ship in `sbs_utils/media`, which
resolves as the last media root (see test_library_media_root).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import os
import shutil
import tempfile
import unittest

import sbs_utils
import sbs_utils.fs as fs
from sbs_utils.procedural import media_paths as MP
from sbs_utils.procedural import ship_data as SD
from sbs_utils.procedural.gui import icon_sheet
from sbs_utils.procedural.gui.image import ImageAtlas

REPO = os.path.dirname(os.path.dirname(os.path.abspath(sbs_utils.__file__)))
MEDIA = os.path.join(REPO, "media")


class _NoLMMission(unittest.TestCase):
    """A mission that pins the library and nothing else."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.mission = os.path.join(self.root, "Plain")
        os.makedirs(os.path.join(self.mission, "media"))
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump({"sbslib": ["artemis-sbs.sbs_utils.v1.4.0.sbslib"]}, f)
        old = fs.script_dir
        fs.script_dir = self.mission
        self.addCleanup(setattr, fs, "script_dir", old)
        MP._LIB_MEDIA = MP._MISSION = None
        self.addCleanup(setattr, MP, "_LIB_MEDIA", None)


class TestLibraryIcons(_NoLMMission):
    def setUp(self):
        super().setUp()
        saved = dict(ImageAtlas.all)
        self.addCleanup(lambda: (ImageAtlas.all.clear(), ImageAtlas.all.update(saved)))
        for n in icon_sheet._LIBRARY_ICON_NAMES:
            ImageAtlas.all.pop(ImageAtlas.qualify(n, icon_sheet.ICON_DOMAIN), None)
        icon_sheet._library_icons_for = None
        self.addCleanup(setattr, icon_sheet, "_library_icons_for", None)

    def test_EPADD_ICONS_RESOLVE_WITHOUT_LM(self):
        index, key = icon_sheet.icon_resolve("epadd.status")
        self.assertIsNone(index)
        self.assertEqual(key, ImageAtlas.qualify("epadd.status", icon_sheet.ICON_DOMAIN))
        self.assertIn("epadd/icons", ImageAtlas.all[key].get_props(None))

    def test_a_claim_already_made_is_not_overwritten(self):
        from sbs_utils.procedural.gui.icon import gui_icon_add_atlas
        gui_icon_add_atlas("epadd.cargo", "media/mine", 0, 0, 10, 10)
        icon_sheet.icon_resolve("epadd.status")
        props = ImageAtlas.all[ImageAtlas.qualify("epadd.cargo", "icon")].get_props(None)
        self.assertIn("media/mine", props)

    def test_built_in_names_do_not_touch_the_sheet(self):
        self.assertEqual(icon_sheet.icon_resolve("square")[0] is not None, True)
        self.assertIsNone(icon_sheet._library_icons_for)


class TestLibraryShipData(_NoLMMission):
    def setUp(self):
        super().setUp()
        self.addCleanup(SD.extra_ship_data_force, None)
        self.addCleanup(SD.ship_data_reset_for_mission)
        SD.ship_data_reset_for_mission()
        SD.ship_data_cache = {"#ship-list": []}
        SD.extra_ship_data_force(True)

    def test_EVA_HULL_DECLARES_WITHOUT_LM(self):
        SD.add_extra("lm_eva_ships")
        self.assertIsNotNone(SD.get_ship_data_for("lm_eva_suit"))

    def test_turrets_declare_without_lm(self):
        SD.add_extra("turrets/extraShipData_turrets")
        self.assertIsNotNone(SD.get_ship_data_for("lm_turret_beam"))


class TestShipDataFilesAreEngineShaped(unittest.TestCase):
    """Strict JSON (the user's rule until the engine reads YAML), final newline (the engine
    rejects a file without one), and art that is really in the pack."""

    FILES = ("lm_eva_ships.json", "turrets/extraShipData_turrets.json")

    def test_strict_json_with_a_final_newline(self):
        for rel in self.FILES:
            with open(os.path.join(MEDIA, rel), encoding="utf-8") as f:
                text = f.read()
            json.loads(text)
            self.assertTrue(text.endswith("\n"), rel)
            self.assertTrue(SD._looks_like_hjson(text), rel)

    def test_eva_art_points_into_THIS_pack_and_exists(self):
        with open(os.path.join(REPO, "__lib__.json")) as f:
            version = json.load(f)["version"]
        with open(os.path.join(MEDIA, "lm_eva_ships.json"), encoding="utf-8") as f:
            entry = json.load(f)["#ship-list"][0]
        pack = f"artemis-sbs.sbs_utils.media.{version}"
        prefix = f"data/missions/__lib__/media/{pack}/"
        self.assertTrue(entry["artfileroot"].startswith(prefix), entry["artfileroot"])
        rel = entry["artfileroot"][len(prefix):]
        self.assertTrue(os.path.isfile(os.path.join(MEDIA, rel + ".obj")))

    def test_epadd_sheet_matches_its_declared_grid(self):
        path, cols, rows, cell, names = icon_sheet.LIBRARY_ICON_SHEETS[0]
        self.assertTrue(os.path.isfile(os.path.join(MEDIA, path + ".png")))
        self.assertLessEqual(len(names), cols * rows)


if __name__ == "__main__":
    unittest.main()
