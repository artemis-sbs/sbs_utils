"""A race declares its own raiding fleet ladder, and can be turned off.

The ladders were six `siege_<race>_fleet` literals in
`LegendaryMissions/fleets/map_common.py` - about 420 lines - reached through a seven-branch
`if race == "..."` chain, with the roster of factions that can raid written as a
`random.choice([...])` literal beside it. Adding a race meant editing a mission library,
and a mod could not add one at all.

The registry lives in `sbs_utils` rather than in LegendaryMissions because MAST addons
compile in a NON-DETERMINISTIC order: a race addon calling a function defined in the
`fleets` addon would work or not depending on which got there first.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural import fleet_tables as ft
from sbs_utils.procedural import settings as S


_KRALIEN = """
race: kralien
fleets:
  - [[kralien_cruiser], [kralien_cruiser, kralien_cruiser]]
  - [[kralien_battleship]]
"""

_PIRATE = """
race: pirate
fleets:
  - [[pirate_longbow]]
"""


class TestFleetTables(unittest.TestCase):
    def setUp(self):
        ft.fleet_tables_reset()

    def tearDown(self):
        ft.fleet_tables_reset()

    def test_a_race_registers_its_ladder_from_yaml(self):
        ft.fleet_table_load_yaml(_KRALIEN, "race_kralien")
        self.assertTrue(ft.fleet_table_has("kralien"))
        self.assertEqual(ft.fleet_table_get("kralien", 0, 0), ["kralien_cruiser"])
        self.assertEqual(ft.fleet_table_get("kralien", 1, 0), ["kralien_battleship"])

    def test_race_matching_ignores_case(self):
        ft.fleet_table_load_yaml(_KRALIEN, "race_kralien")
        self.assertEqual(ft.fleet_table_get("KRALIEN", 0, 0), ["kralien_cruiser"])
        self.assertEqual(ft.fleet_table_get("  Kralien ", 0, 0), ["kralien_cruiser"])

    def test_difficulty_is_clamped_not_indexed_off_the_end(self):
        """A caller asking for tier 99 of a 2-tier ladder should get the top tier, not an
        IndexError in the middle of a spawn."""
        ft.fleet_table_load_yaml(_KRALIEN, "race_kralien")
        self.assertEqual(ft.fleet_table_get("kralien", 99, 0), ["kralien_battleship"])
        self.assertEqual(ft.fleet_table_get("kralien", -5, 0), ["kralien_cruiser"])

    def test_an_unregistered_race_returns_empty_not_an_error(self):
        self.assertEqual(ft.fleet_table_get("vulcan", 0), [])

    def test_random_picks_only_among_registered_races(self):
        """The roster used to be a literal. A race now joins the rotation by existing."""
        ft.fleet_table_load_yaml(_PIRATE, "race_pirate")
        for _ in range(20):
            self.assertEqual(ft.fleet_table_get("random", 0), ["pirate_longbow"])

    def test_random_with_nothing_registered_is_empty(self):
        self.assertEqual(ft.fleet_table_get("random", 0), [])

    def test_the_returned_list_is_a_copy(self):
        """A caller mutating its fleet must not edit the ladder for every later spawn."""
        ft.fleet_table_load_yaml(_KRALIEN, "race_kralien")
        got = ft.fleet_table_get("kralien", 0, 0)
        got.append("kralien_dreadnought")
        self.assertEqual(ft.fleet_table_get("kralien", 0, 0), ["kralien_cruiser"])

    def test_junk_yaml_is_ignored_not_fatal(self):
        for bad in (None, "", "[]", "race: kralien", "fleets: [[[a]]]"):
            self.assertIsNone(ft.fleet_table_load_yaml(bad, "bad"))

    def test_a_collision_between_two_mods_is_reported(self):
        from sbs_utils.procedural import execution
        said = []
        real = execution.log
        execution.log = lambda msg, *a, **k: said.append(msg)
        try:
            ft.fleet_table_load_yaml(_KRALIEN, "race_kralien")
            ft.fleet_table_load_yaml(_KRALIEN, "other_mod")
        finally:
            execution.log = real
        self.assertTrue(any("collision" in m for m in said), said)

    def test_reset_drops_every_ladder(self):
        """Per-mission state: the next mission has its own enabled races, and inheriting
        these would let it spawn fleets for a race it never turned on."""
        ft.fleet_table_load_yaml(_KRALIEN, "race_kralien")
        self.assertEqual(ft.fleet_tables_count(), 1)
        from sbs_utils.handlerhooks import reset_mission_state
        reset_mission_state()
        self.assertEqual(ft.fleet_tables_count(), 0)

    def test_registered_in_the_reset_ledger(self):
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("fleet_tables", _RESET_PROBES)


class TestCanField(unittest.TestCase):
    """A race can be REAL and still not be fieldable.

    The TNG pack's Breen is a shipData side with a hull and an interior, and two of its
    theaters roster it - but its hull lives in the DOMINION ladder and it had no
    `fleets.yaml` of its own. `fleet_create` returned None and the raider prefab died on
    `brain_add(fleet.id, ...)` with `'NoneType' object has no attribute 'id'`, which names
    neither the race nor the missing file. Every Breen roll was that error.

    So the roster gate is "has a ladder", and it SAYS which race it dropped.
    """

    def setUp(self):
        ft.fleet_tables_reset()
        ft.fleet_table_load_yaml(_KRALIEN, "race_kralien")

    def tearDown(self):
        ft.fleet_tables_reset()

    def test_a_race_with_a_ladder_can_field(self):
        self.assertTrue(ft.fleet_table_can_field("Kralien"))
        self.assertTrue(ft.fleet_table_can_field("  KRALIEN "))

    def test_a_race_with_no_ladder_cannot(self):
        self.assertFalse(ft.fleet_table_can_field("breen"))

    def test_it_names_the_race_once(self):
        import contextlib, io as _io
        out = _io.StringIO()
        with contextlib.redirect_stdout(out):
            ft.fleet_table_can_field("breen")
            ft.fleet_table_can_field("breen")
            ft.fleet_table_can_field("Breen")
        said = out.getvalue()
        self.assertEqual(said.count("breen"), 1, said)
        self.assertIn("no fleet ladder", said)

    def test_the_warning_is_re_armed_by_the_mission_reset(self):
        """The latch is per-mission. `cosmos_dev` reuses one interpreter, so a warning
        held across the boundary would go unsaid for the mission that still has the bug.
        """
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()):
            ft.fleet_table_can_field("breen")
        ft.fleet_tables_reset()
        out = _io.StringIO()
        with contextlib.redirect_stdout(out):
            ft.fleet_table_can_field("breen")
        self.assertIn("breen", out.getvalue())


class TestNpcRaces(unittest.TestCase):
    def setUp(self):
        S.setting_defaults = None
        S.settings_get_defaults()

    def tearDown(self):
        S.setting_defaults = None

    def test_npc_and_playable_are_separate_questions(self):
        """Most missions want few playable races and many that raid them."""
        S.settings_get_defaults()["PLAYABLE_RACES"] = "TSN"
        S.settings_get_defaults()["NPC_RACES"] = "Kralien, Pirate"
        self.assertTrue(S.settings_race_is_playable("TSN"))
        self.assertFalse(S.settings_race_is_npc("TSN"))
        self.assertTrue(S.settings_race_is_npc("Kralien"))
        self.assertFalse(S.settings_race_is_playable("Kralien"))

    def test_matching_ignores_case_and_spacing(self):
        S.settings_get_defaults()["NPC_RACES"] = "  kralien , PIRATE "
        for r in ("Kralien", "KRALIEN", "  pirate  "):
            self.assertTrue(S.settings_race_is_npc(r), r)

    def test_empty_means_no_restriction(self):
        S.settings_get_defaults()["NPC_RACES"] = ""
        self.assertTrue(S.settings_race_is_npc("anything"))

    def test_the_default_covers_every_race_that_ships_a_ladder(self):
        for race in ("Kralien", "Torgoth", "Arvonian", "Skaraan", "Ximni", "Pirate"):
            self.assertTrue(S.settings_race_is_npc(race),
                            f"{race} ships a fleets.yaml but is not in the default")



class TestMastCanCallThem(unittest.TestCase):
    """A procedural module is invisible to MAST until it is added to the import list in
    `mast_sbs/mast_sbs_procedural.py`.

    This is not theoretical. `fleet_tables` shipped without that line: the unit tests
    passed, the headless conformance run passed, and the first ENGINE run died with a
    NameError inside the addon that supplies the enemies. Nothing else checks it, because
    Python code that imports the module directly never notices.
    """

    def test_the_race_addon_entry_points_are_mast_globals(self):
        import sys
        import cosmos_dev.mock.sbs as mock
        sys.modules.setdefault("sbs", mock)
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        from sbs_utils.mast.mast_globals import MastGlobals

        # Every function a race_*/__init__.mast line calls.
        for name in ("fleet_table_load_yaml", "fleet_table_get", "fleet_table_has",
                     "fleet_table_races", "fleet_table_pick_race",
                     "settings_race_is_npc", "settings_race_is_playable",
                     "grid_merge_ascii", "grid_get_layout"):
            self.assertIn(name, MastGlobals.globals,
                          f"{name} is not callable from MAST - add its module to the "
                          "import list in mast_sbs/mast_sbs_procedural.py")

if __name__ == "__main__":
    unittest.main()
