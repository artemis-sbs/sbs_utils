"""A THEATER declares WHO a mission fights; the map keeps its own weight curve.

The bug that prompted it: LM picks its enemy race from literals, so under a total
conversion the mix is whatever the hull-shape pairing happened to produce - at difficulty 5
siege is [70, 10, 10, 10] and the 70% slot went to a minor faction, so nearly every enemy
was that faction and the canonical ones almost never appeared.

Two things these tests pin hardest:

  * NO THEATER SET MUST BE IDENTITY. Every accessor returns None/{} so a caller keeps its
    own literal list. That is the whole backward-compatibility story.
  * THE MAP'S CURVE SURVIVES. LM's curve diversifies the enemy mix as difficulty rises
    ([85,5,5,5] -> [10,30,30,30]); a theater that flattened it would silently remove a
    design feature, and nothing would error.

    python -m unittest tests.test_amd_theater
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import collections
import random
import unittest

from sbs_utils.procedural import amd_theater as T


DOC = """
# [Dominion War](dominion_war)
---
Factions: cardassian, dominion, breen, klingon
Faces: cardassian=cardassian, dominion=jemhadar, breen=vorta
Music: TNG_Music
---
The Alpha Quadrant at war.

# [Klingon War](klingon_war)
---
Factions: klingon, romulan, orion, kazon
---
Blood and honor.

# [Fixed Mix](fixed_mix)
---
Factions: romulan, klingon
Weights: 90, 10
---
A theater that insists on its own proportions.
"""


class _Settings:
    def __init__(self, values):
        self.values = values

    def __call__(self):
        return self.values


class TheaterTests(unittest.TestCase):

    def setUp(self):
        T.amd_theater_clear()
        import sbs_utils.procedural.settings as S
        self._real = S.settings_get_defaults
        self._set({})
        T.theater_declare_text(DOC)

    def tearDown(self):
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = self._real
        T.amd_theater_clear()

    def _set(self, values):
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = _Settings(values)

    # --- parsing ------------------------------------------------------------

    def test_declares_every_theater(self):
        self.assertEqual(["dominion_war", "fixed_mix", "klingon_war"], T.theater_names())

    def test_factions_keep_their_authored_order(self):
        self.assertEqual(["cardassian", "dominion", "breen", "klingon"],
                         T.theater_factions(key="dominion_war"))

    def test_faces_and_music_are_read(self):
        self.assertEqual("jemhadar", T.theater_faces("dominion_war")["dominion"])
        self.assertEqual("TNG_Music", T.theater_music("dominion_war"))

    def test_a_theater_with_no_factions_is_refused(self):
        T.theater_declare_text("# [Empty](empty)\n---\nMusic: x\n---\n")
        self.assertNotIn("empty", T.theater_names())

    def test_redeclaring_a_key_replaces_it(self):
        T.theater_declare_text("# [DW](dominion_war)\n---\nFactions: orion\n---\n")
        self.assertEqual(["orion"], T.theater_factions(key="dominion_war"))

    # --- no theater set is identity -----------------------------------------

    def test_unset_theater_returns_none(self):
        self.assertIsNone(T.theater_factions())
        self.assertIsNone(T.theater_pick_race([70, 10, 10, 10]))
        self.assertEqual({}, T.theater_faces())
        self.assertIsNone(T.theater_music())

    def test_active_theater_comes_from_the_setting(self):
        self._set({"THEATER": "klingon_war"})
        self.assertEqual("klingon", T.theater_factions()[0])

    def test_setting_is_case_insensitive(self):
        self._set({"THEATER": "Klingon_War"})
        self.assertEqual("klingon", T.theater_factions()[0])

    def test_an_undeclared_theater_reads_as_unset(self):
        self._set({"THEATER": "no_such_theater"})
        self.assertIsNone(T.theater_factions())

    def test_a_shared_variable_selects_the_theater(self):
        """Both LIVE selection paths write a shared variable, not a setting.

        The server panel's Theater dropdown sets `shared THEATER`, and map_apply_defaults
        publishes a map's `Defaults: THEATER:` the same way. settings_get_defaults() is a
        cached merge of yaml + profile and sees neither - so reading only that made a
        theater selectable in exactly ONE place, a profile file, and silently ignored
        everywhere else. Five theaters shipped and four were unreachable.
        """
        from sbs_utils.procedural.execution import set_shared_variable
        set_shared_variable("THEATER", "klingon_war")
        try:
            self.assertEqual("klingon", T.theater_factions()[0])
        finally:
            set_shared_variable("THEATER", None)

    def test_the_setting_still_works_when_no_shared_value_is_set(self):
        self._set({"THEATER": "dominion_war"})
        self.assertEqual("cardassian", T.theater_factions()[0])

    def test_find_resolves_a_display_name_or_a_key(self):
        """The dropdown shows display names; the setting is a key. Something has to
        translate, and it must still accept the key a profile already writes."""
        self.assertEqual("dominion_war", T.theater_find("Dominion War"))
        self.assertEqual("dominion_war", T.theater_find("dominion_war"))
        self.assertEqual("dominion_war", T.theater_find("DOMINION WAR"))
        self.assertIsNone(T.theater_find("none"))
        self.assertIsNone(T.theater_find("no such theater"))

    def test_get_list_is_what_an_operator_control_is_built_from(self):
        keys = [r.get("key") for r in T.theater_get_list()]
        self.assertEqual(["dominion_war", "fixed_mix", "klingon_war"], keys)

    def test_name_list_is_a_dropdown_string(self):
        self.assertEqual("None, Dominion War, Fixed Mix, Klingon War", T.theater_name_list())

    def test_selected_name_seeds_the_var_from_the_setting(self):
        """The `default shared THEATER = theater_selected_name()` line a map writes. Called
        before any shared value exists it must fall through to the SETTING, or a profile's
        THEATER would be overwritten with "None" by the very line meant to seed it."""
        self._set({"THEATER": "klingon_war"})
        self.assertEqual("Klingon War", T.theater_selected_name())

    def test_selected_name_is_None_when_nothing_is_active(self):
        self.assertEqual("None", T.theater_selected_name())

    def test_an_empty_registry_offers_only_None(self):
        T.amd_theater_clear()
        self.assertEqual("None", T.theater_name_list())

    # --- the map's curve is what shapes the mix -----------------------------

    def _hist(self, weights, key, n=6000):
        random.seed(7)
        c = collections.Counter(T.theater_pick_race(weights, key=key) for _ in range(n))
        return {k: round(100.0 * v / n) for k, v in c.items()}

    def test_curve_is_applied_in_faction_order(self):
        h = self._hist([70, 10, 10, 10], "dominion_war")
        self.assertAlmostEqual(70, h["cardassian"], delta=3)
        self.assertAlmostEqual(10, h["klingon"], delta=3)

    def test_the_difficulty_curve_survives(self):
        # LM's real endpoints. If a theater ever flattened these, the enemy mix would stop
        # diversifying with difficulty and nothing would report it.
        easy = self._hist([85, 5, 5, 5], "dominion_war")
        hard = self._hist([10, 30, 30, 30], "dominion_war")
        self.assertAlmostEqual(85, easy["cardassian"], delta=3)
        self.assertAlmostEqual(10, hard["cardassian"], delta=3)

    def test_a_three_slot_map_takes_three_factions(self):
        h = self._hist([50, 25, 25], "dominion_war")
        self.assertNotIn("klingon", h, "a 3-weight curve must not reach the 4th faction")

    def test_fewer_factions_than_slots_cycles_rather_than_dropping_a_slot(self):
        self.assertEqual(["romulan", "klingon", "romulan", "klingon"],
                         T.theater_factions(4, key="fixed_mix"))

    def test_a_theater_weights_block_overrides_the_map_curve(self):
        h = self._hist([50, 50], "fixed_mix")
        self.assertAlmostEqual(90, h["romulan"], delta=3)

    def test_no_weights_anywhere_is_an_even_pick(self):
        random.seed(3)
        c = collections.Counter(T.theater_pick_race(key="klingon_war") for _ in range(4000))
        self.assertEqual(4, len(c))

    def test_lms_whole_difficulty_table_is_reproduced(self):
        """Every row of siege's real curve, not just the endpoints.

        The bug that started all this was a distribution nobody chose, and an endpoint-only
        check would not have caught a theater that quietly flattened the middle of the
        table. maps/siege.mast:190, copied verbatim.
        """
        DIFF_WEIGHT = [[85, 5, 5, 5], [82, 6, 6, 6], [79, 7, 7, 7], [76, 8, 8, 8],
                       [70, 10, 10, 10], [64, 12, 12, 12], [58, 14, 14, 14],
                       [46, 18, 18, 18], [34, 22, 22, 22], [22, 26, 26, 26],
                       [10, 30, 30, 30]]
        factions = T.theater_factions(key="dominion_war")
        for difficulty, weights in enumerate(DIFF_WEIGHT, start=1):
            h = self._hist(weights, "dominion_war")
            for faction, want in zip(factions, weights):
                self.assertAlmostEqual(
                    want, h.get(faction, 0), delta=3,
                    msg=f"difficulty {difficulty}: {faction} wanted ~{want}%, got {h.get(faction, 0)}%")

    def test_no_theater_leaves_the_callers_own_list_alone(self):
        """The fallback LM relies on: unset means the map keeps its literal races.

        `fleet_pick_enemy_race` passes its own list as `names`; with no theater active the
        pick must come back None so the caller falls through to its own random.choices.
        Without this every stock mission's enemy mix would change.
        """
        self.assertIsNone(T.theater_pick_race([70, 10, 10, 10], ["Kralien", "Torgoth"]))

    def test_pick_returns_the_callers_spelling_not_the_theaters(self):
        """LM BRANCHES on these strings - `if enemy1 == "Kralien":` in borderwar and
        deepstrike - so returning the theater's lowercase key would make every branch fall
        through and the map would spawn no enemy stations at all, silently."""
        self._set({"THEATER": "klingon_war"})
        names = ["Klingon", "Romulan", "Orion", "Kazon"]
        for _ in range(50):
            self.assertIn(T.theater_pick_race([70, 10, 10, 10], names), names)

    def test_an_unknown_field_is_named(self):
        """A typo'd fence label is DROPPED, and dropping it silently is how a theater reads
        as working while changing nothing.

        Reported here rather than by `sbs lint`: these headings carry no section name, so
        the linter cannot resolve them to an archetype and calls the file clean whatever is
        in it - verified by putting a deliberately bogus field in theaters.amd and getting
        `clean` back.
        """
        import io
        import contextlib
        doc = chr(10).join([chr(35) + " [Typo](typo)", "---", "Factions: kralien",
                            "Player Facton: Federation", "---", "x", ""])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            T.theater_declare_text(doc)
        out = buf.getvalue()
        self.assertIn("player_facton", out)
        self.assertIn("unknown field", out)
        # Still declared - one bad label must not throw the whole theater away.
        self.assertIn("typo", T.theater_names())

    def test_every_known_field_is_accepted_without_complaint(self):
        """Guards the table against drifting from the handler: a label the handler accepts
        but the table has not heard of would be reported to authors as a typo."""
        import io
        import contextlib
        doc = chr(10).join([
            chr(35) + " [All](all)", "---",
            "Factions: kralien", "Weights: 50, 50", "Art: kralien=Klingon",
            "Faces: kralien=klingon", "Music: X", "Player Faction: Orion",
            "Players: tsn_scout", "Player Side Name: N", "Player Side Color: #fa0",
            "Player Side Icon: 7", "Player Side Key: raider", "---", "x", ""])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            T.theater_declare_text(doc)
        self.assertNotIn("unknown field", buf.getvalue())

    # --- the depth guard ----------------------------------------------------

    def test_depth_report_is_quiet_when_no_ship_table_is_loaded(self):
        # "Cannot judge" is not "is broken": with no ship data every faction counts zero,
        # and reporting them all would train people to ignore the warning.
        self.assertEqual([], T.theater_depth_report([70, 10, 10, 10], key="dominion_war"))

    def test_depth_report_flags_a_thin_faction_in_a_heavy_slot(self):
        import sbs_utils.procedural.ship_data as SD
        real_loaded, real_filter = SD.ship_data_is_loaded, SD.filter_ship_data_by_side
        SD.ship_data_is_loaded = lambda: 1
        # breen has one hull, cardassian has four - the real shape of the TNG pack.
        SD.filter_ship_data_by_side = lambda k, side, role=None, ret_key_only=False: (
            ["a"] if str(side).lower() == "breen" else ["a", "b", "c", "d"])
        try:
            bad = T.theater_depth_report([10, 10, 70, 10], key="dominion_war")
        finally:
            SD.ship_data_is_loaded, SD.filter_ship_data_by_side = real_loaded, real_filter
        self.assertEqual(1, len(bad))
        self.assertEqual("breen", bad[0][0])
        self.assertEqual(1, bad[0][1])

    def test_depth_report_passes_a_deep_faction_in_a_heavy_slot(self):
        import sbs_utils.procedural.ship_data as SD
        real_loaded, real_filter = SD.ship_data_is_loaded, SD.filter_ship_data_by_side
        SD.ship_data_is_loaded = lambda: 1
        SD.filter_ship_data_by_side = lambda k, side, role=None, ret_key_only=False: ["a", "b", "c", "d"]
        try:
            self.assertEqual([], T.theater_depth_report([70, 10, 10, 10], key="dominion_war"))
        finally:
            SD.ship_data_is_loaded, SD.filter_ship_data_by_side = real_loaded, real_filter

    # --- reset ledger -------------------------------------------------------

    def test_clear_empties_the_registry(self):
        self.assertTrue(T.amd_theater_count() > 0)
        T.amd_theater_clear()
        self.assertEqual(0, T.amd_theater_count())


if __name__ == "__main__":
    unittest.main()
