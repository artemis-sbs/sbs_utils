"""Side relations that survive more than one mod.

THE BUG THIS GUARDS. Relations exist only where they are declared - `sides_declare`
applies exactly the `Enemies`/`Allies`/`Neutral` lists and nothing defaults an unnamed
pair. The TNG mod shipped eight factions each naming only `federation`, which made the
matrix a STAR: Federation hostile to all seven, and every other pair (klingon/dominion,
cardassian/klingon) NEUTRAL. Any mission crewing a non-Federation side against a
non-Federation enemy was silently passive.

**It cannot be caught by a conformance run.** What breaks is the shooting, not the script -
every trial in the suite passed for the whole time this was wrong. These are the tests that
can see it, and they are sub-second because they assert the relation table directly.

CROSS-MOD is the part that needs tokens. LegendaryMissions declares tsn/raider/civ and a
total conversion declares its own factions; neither document can name the other's sides
without depending on it, so every cross pair stayed neutral. `players` and `civilians`
resolve across documents; `*` deliberately does not.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural import amd_sides as A
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.sides import side_are_enemies, side_are_neutral, side_are_allies
from sbs_utils.procedural.settings import settings_get_defaults


def _declare(text):
    return A.sides_declare_amd(amd_document(text, data_parser=A.amd_side_data))


class SideAudienceTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)                       # calls reset_mission_state -> amd_sides_clear
        self._settings = settings_get_defaults()
        self._saved = self._settings.get("PLAYER_LIST")
        self._settings["PLAYER_LIST"] = [{"side": "federation"}, {"side": "klingon"}]

    def tearDown(self):
        self._settings["PLAYER_LIST"] = self._saved

    # ---- the cross-mod case ------------------------------------------------
    def test_players_and_civilians_resolve_across_documents(self):
        # Two separate "mods". Neither names the other's sides.
        _declare("# [Federation](federation)\n---\nColor: #07F\n---\nF.\n\n"
                 "# [Klingon](klingon)\n---\nColor: #C30\n---\nK.\n")
        _declare("# [Civ](civ)\n---\nCivilian: true\nNeutral: players\n---\nC.\n\n"
                 "# [Raider](raider)\n---\nEnemies: players, civilians\n---\nR.\n")
        A.sides_apply_audiences()

        self.assertTrue(side_are_enemies("raider", "federation"))
        self.assertTrue(side_are_enemies("raider", "klingon"))
        self.assertTrue(side_are_enemies("raider", "civ"))
        # The crew does not shoot the people they are protecting.
        self.assertTrue(side_are_neutral("civ", "federation"))
        self.assertTrue(side_are_neutral("civ", "klingon"))

    def test_a_civilian_declared_later_still_becomes_prey(self):
        # Declaration order is not authoring order across addons, so the rule has to be
        # replayable rather than resolved once at parse time.
        # The roster sides are declared too, or `players` names sides that do not exist and
        # side_set_relations rightly warns "Side not found" - which is a real diagnostic
        # for a profile pointing at an undeclared side, not noise to suppress.
        _declare("# [Federation](federation)\n---\nColor: #07F\n---\nF.\n\n"
                 "# [Klingon](klingon)\n---\nColor: #C30\n---\nK.\n")
        _declare("# [Raider](raider)\n---\nEnemies: players, civilians\n---\nR.\n")
        _declare("# [Civ](civ)\n---\nCivilian: true\n---\nC.\n")
        A.sides_apply_audiences()
        self.assertTrue(side_are_enemies("raider", "civ"))

    def test_players_picks_up_a_live_ship_side_not_in_the_roster(self):
        # A mission that seats its crew on another side after the sides were declared.
        # EMPTY roster on purpose, so the only thing `players` can resolve to is the live
        # ship - this is the runtime half on its own, not riding on PLAYER_LIST.
        self._settings["PLAYER_LIST"] = []
        _declare("# [Raider](raider)\n---\nEnemies: players\n---\nR.\n"
                 "# [Romulan](romulan)\n---\nColor: #0A6\n---\nR.\n")
        self.assertFalse(side_are_enemies("raider", "romulan"))
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.procedural.query import to_object
        pid = player_spawn(0, 0, 0, "Probe", "romulan", "tsn_battle_cruiser")
        to_object(pid).side = "romulan"
        A.sides_apply_audiences()
        self.assertTrue(side_are_enemies("raider", "romulan"))

    # ---- the within-document wildcard --------------------------------------
    def test_star_makes_every_other_side_in_the_document_hostile(self):
        _declare("# [A](a)\n---\nEnemies: *\n---\nA.\n\n"
                 "# [B](b)\n---\nColor: #111\n---\nB.\n\n"
                 "# [C](c)\n---\nColor: #222\n---\nC.\n")
        self.assertTrue(side_are_enemies("a", "b"))
        self.assertTrue(side_are_enemies("a", "c"))

    def test_explicit_names_beat_the_wildcard(self):
        _declare("# [A](a)\n---\nAllies: b\nEnemies: *\n---\nA.\n\n"
                 "# [B](b)\n---\nColor: #111\n---\nB.\n\n"
                 "# [C](c)\n---\nColor: #222\n---\nC.\n")
        self.assertTrue(side_are_allies("a", "b"))
        self.assertTrue(side_are_enemies("a", "c"))

    def test_star_does_not_reach_another_document(self):
        # An addon must not silently redefine a relation with a side it never heard of.
        _declare("# [Outsider](outsider)\n---\nColor: #333\n---\nO.\n")
        _declare("# [A](a)\n---\nEnemies: *\n---\nA.\n\n"
                 "# [B](b)\n---\nColor: #111\n---\nB.\n")
        self.assertTrue(side_are_enemies("a", "b"))
        self.assertFalse(side_are_enemies("a", "outsider"))

    # ---- back-compatibility -------------------------------------------------
    def test_a_document_with_no_tokens_is_unchanged(self):
        # The whole safety argument for shipping this days before a playtest.
        _declare("# [TSN](tsn)\n---\nEnemies: raider\n---\nT.\n\n"
                 "# [Raider](raider)\n---\nEnemies: tsn, civ\n---\nR.\n\n"
                 "# [Civ](civ)\n---\nNeutral: tsn\n---\nC.\n")
        self.assertTrue(side_are_enemies("tsn", "raider"))
        self.assertTrue(side_are_enemies("raider", "civ"))
        self.assertTrue(side_are_neutral("tsn", "civ"))
        # No tokens seen, so nothing to replay and nothing held over a mission boundary.
        self.assertEqual(A.amd_sides_audience_count(), 0)

    def test_reset_drops_the_registries(self):
        # A module-level container that outlives a mission is how second-run bugs start:
        # the next mission would inherit the previous one's civilians.
        _declare("# [Civ](civ)\n---\nCivilian: true\n---\nC.\n\n"
                 "# [Raider](raider)\n---\nEnemies: civilians\n---\nR.\n")
        self.assertTrue(A.amd_sides_audience_count() > 0)
        reset_mock(sbs)
        self.assertEqual(A.amd_sides_audience_count(), 0)
        self.assertEqual(A.side_civilian_sides(), set())


if __name__ == "__main__":
    unittest.main()
