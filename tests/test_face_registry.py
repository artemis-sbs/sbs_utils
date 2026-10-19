"""Mod-registered face sheets and races.

The six stock races build a face layer by layer out of their atlas. A mod atlas
need not work that way - the TNG sheets are one whole bust per cell - so the
registry stores ready-made face strings and random_face() checks it first.

Two things this exists to protect:

  * the stock races must behave EXACTLY as before. This is the backward-compat
    rule that outranks almost everything else in MAST-facing code.
  * the registry is per-mission module state. A registered face string names an
    atlas alias that only exists while that mod is loaded, so carrying it into
    the next mission would hand mission 2 faces pointing at a sheet the engine is
    no longer told about. reset_mission_state() must empty it.
"""

import sys
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

# handlerhooks does a bare `import sbs`. Without this the ledger tests below only passed
# when some earlier test in the same run had already put the mock there.
from cosmos_dev.mock import sbs as _mock_sbs
sys.modules.setdefault("sbs", _mock_sbs)

from sbs_utils import faces

from sbs_utils.faces import (
    face_mod_reset, face_mod_size, face_overlay, face_register_race,
    face_register_sheet, face_random_registered, face_registered_races,
    face_registered_sheets, face_sheet_grid, random_face,
)


class TestSheetGoesToTheEngine(unittest.TestCase):
    """face_register_sheet(..., filename=) hands the art to the engine (1.3.15)."""

    def setUp(self):
        from sbs_utils.fs import test_set_exe_dir
        test_set_exe_dir()
        from cosmos_dev.mock import sbs
        from sbs_utils.helpers import Context, FakeEvent, FrameContext
        self.sbs = sbs
        self.FrameContext = FrameContext
        sbs.create_new_sim()
        sbs.face_sheets.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0))
        face_mod_reset()
        import logging
        self.said = []

        class _Catch(logging.Handler):
            def emit(_self, record):
                self.said.append(record.getMessage())
        self._handler = _Catch()
        logging.getLogger("mast.runtime").addHandler(self._handler)

    def tearDown(self):
        import logging
        logging.getLogger("mast.runtime").removeHandler(self._handler)
        self.FrameContext.context = None
        face_mod_reset()

    def test_a_sheet_with_its_art_is_registered_with_the_engine(self):
        told = face_register_sheet("tng1", 8, 8, filename="media/faces_tng/TNG_Faces_1")
        self.assertTrue(told)
        self.assertIn("tng1", self.sbs.face_sheets)
        self.assertEqual(face_sheet_grid("tng1"), (8, 8))
        self.assertEqual(self.said, [])

    def test_the_engine_gets_a_root_relative_path_with_no_suffix(self):
        """The shape measured to load: from the Cosmos root, and the engine adds .png."""
        import os
        from sbs_utils.fs import get_mission_dir, get_artemis_dir
        face_register_sheet("tng1", filename="media/faces_tng/TNG_Faces_1.png")
        path = self.sbs.face_sheets["tng1"]
        self.assertFalse(path.lower().endswith(".png"))
        self.assertNotIn("\\", path)
        want = os.path.relpath(os.path.join(get_mission_dir(), "media", "faces_tng",
                                            "TNG_Faces_1"), get_artemis_dir())
        self.assertEqual(path, want.replace(os.sep, "/"))

    def test_without_a_filename_nothing_is_told_to_the_engine(self):
        """What it always did: a grid, for the library and the browser compositor."""
        self.assertIsNone(face_register_sheet("tng1", 8, 8))
        self.assertEqual(self.sbs.face_sheets, {})
        self.assertNotIn("file", face_registered_sheets()["tng1"])

    def test_an_engine_that_cannot_add_the_tag_is_reported_once_not_raised(self):
        """Measured on the 1.3.15 exe of 2026-10-13: a tag the engine does not already
        know raises ValueError. A mod must not die on that - it is told once."""
        def _refuses(tag, filename):
            raise ValueError("null rec from faceGen.recordMap[tag]")
        real = self.sbs.add_face_bitmap_sheet
        self.sbs.add_face_bitmap_sheet = _refuses
        self.addCleanup(setattr, self.sbs, "add_face_bitmap_sheet", real)
        self.assertFalse(face_register_sheet("tng1", filename="media/faces_tng/TNG_Faces_1"))
        self.assertFalse(face_register_sheet("tng1", filename="media/faces_tng/TNG_Faces_1"))
        self.assertEqual(len(self.said), 1, self.said)
        self.assertIn("tng1", self.said[0])
        self.assertIn("null rec", self.said[0])
        # The grid is still registered, so the library and the browser keep working.
        self.assertEqual(face_sheet_grid("tng1"), (8, 8))
        self.assertIs(face_registered_sheets()["tng1"]["engine"], False)

    def test_an_engine_older_than_the_call_is_reported_once(self):
        real = self.sbs.add_face_bitmap_sheet
        del self.sbs.add_face_bitmap_sheet
        self.addCleanup(setattr, self.sbs, "add_face_bitmap_sheet", real)
        self.assertFalse(face_register_sheet("tng1", filename="media/faces_tng/TNG_Faces_1"))
        self.assertEqual(len(self.said), 1)
        self.assertIn("1.3.15", self.said[0])

    def test_with_no_engine_to_ask_it_only_records(self):
        self.FrameContext.context = None
        self.assertIsNone(face_register_sheet("tng1", filename="media/faces_tng/TNG_Faces_1"))
        self.assertEqual(face_registered_sheets()["tng1"]["file"], "media/faces_tng/TNG_Faces_1")
        self.assertEqual(self.said, [])

    def test_a_CELL_SIZE_reaches_the_engine(self):
        """Ship portraits are 256 px cells; the engine slices by the size it is told."""
        self.sbs.face_sheet_cells.clear()
        self.assertTrue(face_register_sheet("shp0", 16, 12, filename="media/ship_portraits/base_0",
                                            cell_w=256, cell_h=256))
        self.assertEqual(self.sbs.face_sheet_cells["shp0"], (256, 256))
        self.assertEqual(face_registered_sheets()["shp0"]["cell"], (256, 256))

    def test_a_512_sheet_is_sent_WITHOUT_a_size(self):
        """So a stock-sized sheet still registers on an exe from before sizeW/sizeH."""
        calls = []
        real = self.sbs.add_face_bitmap_sheet
        self.sbs.add_face_bitmap_sheet = lambda *a: calls.append(a)
        self.addCleanup(setattr, self.sbs, "add_face_bitmap_sheet", real)
        face_register_sheet("tng1", filename="media/faces_tng/TNG_Faces_1")
        self.assertEqual(len(calls[0]), 2)

    def test_an_exe_that_cannot_take_a_size_refuses_a_non_512_sheet(self):
        def _old(tag, filename):
            pass
        real = self.sbs.add_face_bitmap_sheet
        self.sbs.add_face_bitmap_sheet = _old
        self.addCleanup(setattr, self.sbs, "add_face_bitmap_sheet", real)
        self.assertFalse(face_register_sheet("shp0", 16, 12, filename="media/x", cell_w=256,
                                             cell_h=256))
        self.assertEqual(len(self.said), 1)
        self.assertIn("256x256", self.said[0])
        self.assertEqual(face_sheet_grid("shp0"), (16, 12))   # the browser still knows it

    def test_a_mission_swap_forgets_the_mocks_sheets_but_a_new_sim_does_not(self):
        """The engine keeps a registered sheet across create_new_sim (measured)."""
        face_register_sheet("tng1", filename="media/faces_tng/TNG_Faces_1")
        self.sbs.create_new_sim()
        self.assertIn("tng1", self.sbs.face_sheets)
        self.sbs.run_next_mission("anything")
        self.sbs.pop_next_mission()
        self.assertEqual(self.sbs.face_sheets, {})


class TestFaceRegistry(unittest.TestCase):
    def setUp(self):
        face_mod_reset()

    def tearDown(self):
        face_mod_reset()

    # --- the stock races are not allowed to change ---------------------------

    def test_stock_races_unchanged(self):
        for race, alias in (("terran", "ter"), ("skaraan", "ska"), ("torgoth", "tor"),
                            ("kralien", "kra"), ("ximni", "zim"), ("arvonian", "arv")):
            f = random_face(race)
            self.assertTrue(f.startswith(alias + " "), "%s -> %r" % (race, f))

    def test_stock_grid(self):
        # Since the 2026-09 redraw every stock sheet has its own size. cosmos_dev's
        # face.js carries the same table (STOCK_GRID) and sbs_cli's face_bake.py scrapes
        # it from there, so a mismatch here silently samples the wrong cell everywhere a
        # face is drawn outside the engine.
        self.assertEqual(face_sheet_grid("ter"), (24, 7))
        self.assertEqual(face_sheet_grid("tor"), (11, 5))
        self.assertEqual(face_sheet_grid("ska"), (7, 5))
        self.assertEqual(face_sheet_grid("kra"), (6, 6))
        self.assertEqual(face_sheet_grid("zim"), (8, 5))
        self.assertEqual(face_sheet_grid("arv"), (8, 4))

    def test_stock_grid_agrees_with_face_js(self):
        """The mock compositor's copy of the grid must not drift from this one.

        They are separate files in separate languages and nothing but this test couples
        them. A drift does not fail anywhere - it just draws a slice of the wrong cell,
        which reads as "the art is broken" rather than "two tables disagree".
        """
        import os
        import re
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "cosmos_dev", "mockgui", "face.js")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        block = re.search(r"STOCK_GRID\s*=\s*\{(.*?)\}\s*;", src, re.S)
        self.assertIsNotNone(block, "face.js no longer declares STOCK_GRID")
        found = {m.group(1): (int(m.group(2)), int(m.group(3)))
                 for m in re.finditer(r"(\w+)\s*:\s*\{\s*cols\s*:\s*(\d+)\s*,\s*rows\s*:\s*(\d+)",
                                      block.group(1))}
        self.assertEqual(found, dict(faces.FACE_SHEETS))

    def test_unknown_race_still_falls_back(self):
        # Must not raise: callers pass arbitrary side/race strings.
        self.assertTrue(random_face("nosuchrace").startswith("ter "))

    def test_unregistered_race_reads_as_absent(self):
        self.assertIsNone(face_random_registered("klingon"))

    # --- registration --------------------------------------------------------

    def test_registered_race_resolves(self):
        face_register_race("klingon", ["tng1 #fff 3 2;"])
        self.assertEqual(random_face("klingon"), "tng1 #fff 3 2;")

    def test_role_filter_and_fallback(self):
        face_register_race("klingon", ["tng1 #fff 3 2;"],
                           roles={"command": ["tng1 #fff 1 1;"]})
        self.assertEqual(random_face("klingon", "command"), "tng1 #fff 1 1;")
        # A role with no faces falls back to the race pool: asking for a Breen
        # science officer should still get a Breen, not nothing.
        self.assertEqual(random_face("klingon", "science"), "tng1 #fff 3 2;")

    def test_race_is_case_insensitive(self):
        face_register_race("Klingon", ["tng1 #fff 3 2;"])
        self.assertEqual(random_face("KLINGON"), "tng1 #fff 3 2;")

    def test_sheet_registration(self):
        face_register_sheet("tng1", 8, 8)
        self.assertEqual(face_sheet_grid("tng1"), (8, 8))
        self.assertIn("tng1", face_registered_sheets())

    def test_in_random_opt_out(self):
        # A mod that only wants its faces when asked for BY NAME. Without this,
        # loading the mod for its ships would quietly restyle every stock crowd.
        face_register_race("klingon", ["tng1 #fff 3 2;"], in_random=False)
        self.assertEqual(face_registered_races(in_random_only=True), [])
        self.assertEqual(face_registered_races(), ["klingon"])
        self.assertEqual(random_face("klingon"), "tng1 #fff 3 2;")

    def test_bare_random_can_reach_registered_races(self):
        face_register_race("klingon", ["tng1 #fff 3 2;"])
        seen = set(random_face() for _ in range(400))
        self.assertIn("tng1 #fff 3 2;", seen)

    # --- overlays ------------------------------------------------------------

    def test_face_overlay_stacks_layers(self):
        self.assertEqual(
            face_overlay("tng1 #fff 3 2;", "tng6 #fff 2 1", "tng6 #fff 5 3;"),
            "tng1 #fff 3 2;tng6 #fff 2 1;tng6 #fff 5 3;")

    def test_face_overlay_skips_empty(self):
        # Callers pass an optional overlay straight in; None must not become ";;".
        self.assertEqual(face_overlay("tng1 #fff 3 2;", None, ""), "tng1 #fff 3 2;")

    def test_face_overlay_works_on_a_stock_face(self):
        # The point of overlays: assimilate a face that was never drawn with implants.
        base = random_face("terran")
        out = face_overlay(base, "tng6 #fff 2 1")
        self.assertTrue(out.startswith("ter "))
        self.assertTrue(out.endswith("tng6 #fff 2 1;"))

    # --- reset ---------------------------------------------------------------

    def test_reset_empties_the_registry(self):
        face_register_sheet("tng1")
        face_register_race("klingon", ["tng1 #fff 3 2;"])
        self.assertEqual(face_mod_size(), 2)
        face_mod_reset()
        self.assertEqual(face_mod_size(), 0)
        self.assertEqual(face_registered_races(), [])
        self.assertTrue(random_face("klingon").startswith("ter "))


class TestFaceRegistryIsInTheResetLedger(unittest.TestCase):
    """A container the ledger does not know about is invisible to the restart soak."""

    def test_registered_with_the_ledger(self):
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("mod face registry", _RESET_PROBES)

    def test_reset_mission_state_clears_it(self):
        from sbs_utils.handlerhooks import reset_mission_state
        face_register_sheet("tng1")
        face_register_race("klingon", ["tng1 #fff 3 2;"])
        try:
            reset_mission_state()
        finally:
            leftover = face_mod_size()
            face_mod_reset()
        self.assertEqual(leftover, 0)


if __name__ == "__main__":
    unittest.main()
