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

import unittest

from sbs_utils.faces import (
    face_mod_reset, face_mod_size, face_overlay, face_register_race,
    face_register_sheet, face_random_registered, face_registered_races,
    face_registered_sheets, face_sheet_grid, random_face,
)


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
        # The Terran sheet is 15 columns; every other stock sheet is 8. face.js
        # hard-codes the same rule, and a mismatch silently samples the wrong cell.
        self.assertEqual(face_sheet_grid("ter"), (15, 8))
        for a in ("ska", "tor", "kra", "zim", "arv"):
            self.assertEqual(face_sheet_grid(a), (8, 8))

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
