"""Ship portraits: one sheet of pre-rendered hulls, drawn as images or as faces.

What this protects:
  * a set registers every page as a FACE sheet with its real cell size (256, not 512)
    and every cell as an image in the `ship` domain;
  * a mod's set wins over the base for a hull both carry - and the base, loading later,
    does not quietly re-point the mod's atlas cell;
  * a hull with no portrait answers None (callers fall back to the live 3D ship);
  * it is per-mission state, cleared by reset_mission_state().
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import os
import shutil
import sys
import tempfile
import unittest

from cosmos_dev.mock import sbs as _mock_sbs
sys.modules.setdefault("sbs", _mock_sbs)

import sbs_utils.fs as fs
from sbs_utils import faces
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural import media_paths as MP
from sbs_utils.procedural import ship_portraits as P
from sbs_utils.procedural.gui.image import ImageAtlas


def _manifest(folder, set_name, cells, extras=None, alias=None, rows=2, silhouettes=None):
    os.makedirs(folder, exist_ok=True)
    data = {"format": 1, "set": set_name, "cell": [256, 256], "cols": 16,
            "pages": [{"file": f"{set_name}_0", "rows": rows}],
            "cells": {k: {"page": 0, "col": c, "row": r} for k, (c, r) in cells.items()},
            "extras": {k: {"page": 0, "col": c, "row": r}
                       for k, (c, r) in (extras or {}).items()}}
    if silhouettes is not None:
        data["silhouettes"] = {k: {"page": 0, "col": c, "row": r}
                               for k, (c, r) in silhouettes.items()}
    if alias:
        data["alias"] = alias
    with open(os.path.join(folder, set_name + ".json"), "w") as f:
        json.dump(data, f)
    open(os.path.join(folder, f"{set_name}_0.png"), "wb").close()


class _Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.mission = os.path.join(self.root, "M")
        os.makedirs(os.path.join(self.mission, "media"))
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump({"sbslib": []}, f)
        old = fs.script_dir
        fs.script_dir = self.mission
        self.addCleanup(setattr, fs, "script_dir", old)
        # The working tree's sbs_utils/media is the library root in tests; point the
        # library root at a folder this test owns instead.
        self.libmedia = os.path.join(self.root, "libmedia")
        os.makedirs(self.libmedia)
        real = MP._library_tree_media
        MP._library_tree_media = lambda: self.libmedia
        self.addCleanup(setattr, MP, "_library_tree_media", real)
        MP._LIB_MEDIA = MP._MISSION = None
        self.addCleanup(setattr, MP, "_LIB_MEDIA", None)
        _mock_sbs.create_new_sim()
        _mock_sbs.face_sheets.clear()
        _mock_sbs.face_sheet_cells.clear()
        FrameContext.context = Context(_mock_sbs.sim, _mock_sbs, FakeEvent(0))
        P.ship_portrait_clear()
        faces.face_mod_reset()
        self.addCleanup(P.ship_portrait_clear)
        self.addCleanup(faces.face_mod_reset)
        saved = dict(ImageAtlas.all)
        self.addCleanup(lambda: (ImageAtlas.all.clear(), ImageAtlas.all.update(saved)))


class TestLoad(_Base):
    def test_A_SET_IS_A_FACE_SHEET_AND_AN_IMAGE_ATLAS(self):
        _manifest(os.path.join(self.mission, "media", "ship_portraits"), "tng",
                  {"tng_galaxy": (3, 1)}, alias="shp_tng")
        n = P.ship_portrait_load("media/ship_portraits/tng")
        self.assertEqual(n, 1)
        self.assertEqual(P.ship_portrait_face("tng_galaxy"), "shp_tng0 #fff 3 1;")
        self.assertEqual(_mock_sbs.face_sheet_cells["shp_tng0"], (256, 256))
        props = P.ship_portrait_props("tng_galaxy")
        self.assertIn("sub_rect:768,256,1024,512", props)
        self.assertIn("ship_portraits/tng_0", props)

    def test_alias_defaults_from_the_set_name(self):
        _manifest(os.path.join(self.mission, "media", "sp"), "venus", {"v1": (0, 0)})
        P.ship_portrait_load("media/sp/venus")
        self.assertTrue(P.ship_portrait_face("v1").startswith("shp_venus0 "))

    def test_a_LOGICAL_path_finds_the_manifest_in_any_pack(self):
        """Two packs both with ship_portraits/ - each set is found by its own manifest,
        not by whichever folder media_shared("ship_portraits") would answer first."""
        lib = os.path.join(self.root, "__lib__", "media")
        _manifest(os.path.join(lib, "u.A.media.v1", "ship_portraits"), "aaa", {"a1": (0, 0)})
        _manifest(os.path.join(lib, "u.B.media.v1", "ship_portraits"), "bbb", {"b1": (1, 0)})
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump({"sbslib": [], "shared_media": ["u.A.media.v1.zip", "u.B.media.v1.zip"]}, f)
        MP._LIB_MEDIA = MP._MISSION = None
        self.assertEqual(P.ship_portrait_load("ship_portraits/bbb"), 1)
        self.assertEqual(P.ship_portrait_load("ship_portraits/aaa"), 1)
        self.assertEqual(P.ship_portrait_face("b1"), "shp_bbb0 #fff 1 0;")
        # media_shared's own fallback spelling resolves the same way
        self.assertEqual(P.ship_portrait_load("media/ship_portraits/bbb"), 1)

    def test_a_missing_manifest_is_zero_not_an_exception(self):
        self.assertEqual(P.ship_portrait_load("media/nope/none"), 0)

    def test_no_portrait_is_None(self):
        self.assertIsNone(P.ship_portrait_face("tsn_light_cruiser"))
        self.assertIsNone(P.ship_portrait_image("tsn_light_cruiser"))
        self.assertFalse(P.ship_portrait_has("tsn_light_cruiser"))


class TestBaseAndMods(_Base):
    def setUp(self):
        super().setUp()
        _manifest(os.path.join(self.libmedia, "ship_portraits"), "base",
                  {"tsn_light_cruiser": (0, 0), "kralien_cruiser": (1, 0)},
                  extras={"unknown": (15, 1)})

    def test_THE_BASE_SET_LOADS_ITSELF(self):
        self.assertTrue(P.ship_portrait_has("tsn_light_cruiser"))
        self.assertEqual(P.ship_portrait_face("kralien_cruiser"), "shp_base0 #fff 1 0;")

    def test_a_MOD_wins_and_the_base_does_not_take_its_atlas_cell_back(self):
        _manifest(os.path.join(self.mission, "media", "ship_portraits"), "mod",
                  {"tsn_light_cruiser": (5, 0)})
        P.ship_portrait_load("media/ship_portraits/mod")
        # the base loads lazily AFTER the mod
        self.assertTrue(P.ship_portrait_has("kralien_cruiser"))
        self.assertEqual(P.ship_portrait_face("tsn_light_cruiser"), "shp_mod0 #fff 5 0;")
        self.assertIn("ship_portraits/mod_0", P.ship_portrait_props("tsn_light_cruiser"))

    def test_stages(self):
        self.assertEqual(P.ship_portrait_stage_face("tsn_light_cruiser", "unknown"),
                         "shp_base0 #fff 15 1;")
        self.assertEqual(P.ship_portrait_stage_face("tsn_light_cruiser", "hull"),
                         "shp_base0 #fff 0 0;")
        self.assertEqual(P.ship_portrait_stage_face("tsn_light_cruiser", "captain",
                                                    captain="ter #fff 0 0;"),
                         "ter #fff 0 0;")
        # no captain yet -> the hull; no hull portrait -> the unknown contact
        self.assertEqual(P.ship_portrait_stage_face("tsn_light_cruiser", "captain"),
                         "shp_base0 #fff 0 0;")
        self.assertEqual(P.ship_portrait_stage_face("not_a_hull", "hull"),
                         "shp_base0 #fff 15 1;")

    def test_an_extra_cannot_be_confused_with_a_hull(self):
        self.assertIsNone(P.ship_portrait_face("unknown"))

    def test_keys(self):
        self.assertEqual(P.ship_portrait_keys(), ["kralien_cruiser", "tsn_light_cruiser"])


class _Rec:
    """Records the engine sends a text-area segment makes."""
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("send_gui_"):
            return lambda *a: self.calls.append((name, a))
        raise AttributeError(name)


class TestTextAreaUsesThePortrait(_Base):
    def setUp(self):
        super().setUp()
        _manifest(os.path.join(self.libmedia, "ship_portraits"), "base",
                  {"tsn_light_cruiser": (2, 0)})

    def _ship_line(self, url):
        from sbs_utils.pages.layout.text_area import ShipLine
        from sbs_utils.vec import Vec3
        return ShipLine(url, Vec3(1000, 1000, 0))

    def test_A_SHIP_EMBED_WITH_A_PORTRAIT_IS_AN_IMAGE(self):
        rec = _Rec()
        self._ship_line("tsn_light_cruiser?height=100").send_gui(rec, 1, "r", "t", 0, 0, 50, 10)
        self.assertEqual([c[0] for c in rec.calls], ["send_gui_image"])
        self.assertIn("sub_rect:512,0,768,256", rec.calls[0][1][3])

    def test_live_keeps_the_3d_ship(self):
        rec = _Rec()
        self._ship_line("tsn_light_cruiser?height=100&live=1").send_gui(rec, 1, "r", "t",
                                                                       0, 0, 50, 10)
        self.assertEqual([c[0] for c in rec.calls], ["send_gui_3dship"])

    def test_no_portrait_falls_back_to_3d(self):
        rec = _Rec()
        self._ship_line("kralien_cruiser?height=100").send_gui(rec, 1, "r", "t", 0, 0, 50, 10)
        self.assertEqual(rec.calls[0][0], "send_gui_3dship")
        self.assertIn("hull_tag:kralien_cruiser;", rec.calls[0][1][3])

    def test_the_lead_too(self):
        from sbs_utils.pages.layout.text_area import _lead_send
        rec = _Rec()
        _lead_send(rec, 1, "r", "t", "ship", "tsn_light_cruiser", 0, 0, 10, 10)
        self.assertEqual(rec.calls[0][0], "send_gui_image")


class TestSilhouettes(_Base):
    def setUp(self):
        super().setUp()
        _manifest(os.path.join(self.libmedia, "ship_portraits"), "base",
                  {"tsn_light_cruiser": (1, 0)}, extras={"unknown": (0, 0)},
                  silhouettes={"tsn_light_cruiser": (2, 0)})

    def test_THE_CONTACT_STAGE_IS_THE_SILHOUETTE_IN_ITS_COLOR(self):
        self.assertEqual(P.ship_portrait_stage_face("tsn_light_cruiser", "contact"),
                         "shp_base0 #9ab 2 0;")
        self.assertEqual(P.ship_portrait_stage_face("tsn_light_cruiser", "contact",
                                                    silhouette_color="#f00"),
                         "shp_base0 #f00 2 0;")
        # the other stages are untouched
        self.assertEqual(P.ship_portrait_stage_face("tsn_light_cruiser", "hull"),
                         "shp_base0 #fff 1 0;")

    def test_silhouette_image_is_its_own_domain(self):
        from sbs_utils.procedural.gui.image import ImageAtlas
        key = P.ship_portrait_silhouette_image("tsn_light_cruiser")
        self.assertEqual(key, "ship.silhouette:tsn_light_cruiser")
        self.assertIn("sub_rect:512,0,768,256", ImageAtlas.all[key].get_props("#9ab"))

    def test_no_silhouette_falls_back_to_unknown(self):
        self.assertIsNone(P.ship_portrait_silhouette_face("kralien_cruiser"))
        self.assertEqual(P.ship_portrait_stage_face("kralien_cruiser", "contact"),
                         "shp_base0 #fff 0 0;")


class TestOldSheetHasNoSilhouettes(_Base):
    def test_a_sheet_without_the_section_still_loads(self):
        _manifest(os.path.join(self.mission, "media", "sp"), "old", {"a": (0, 0)})
        self.assertEqual(P.ship_portrait_load("media/sp/old"), 1)
        self.assertIsNone(P.ship_portrait_silhouette_face("a"))


class TestReset(_Base):
    def test_cleared_by_reset_mission_state_and_in_the_ledger(self):
        from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
        _manifest(os.path.join(self.mission, "media", "sp"), "m", {"a": (0, 0)})
        P.ship_portrait_load("media/sp/m")
        self.assertIn("ship portraits", reset_mission_audit())
        reset_mission_state()
        self.assertNotIn("ship portraits", reset_mission_audit())


if __name__ == "__main__":
    unittest.main()
