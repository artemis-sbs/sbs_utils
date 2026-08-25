"""A RACE is a shipData ``origin``, so a mod joins the roster by EXISTING.

The pinning here is mostly about DERIVATION, because that is the claim: nothing has to be
declared for a race to be usable, and the facts each LM map used to hardcode in an
``if enemy1 == "Kralien":`` chain come back out of the ship table.

The one worth reading is `test_a_race_without_a_station_says_so`. borderwar and deepstrike
list three races where the other maps list four, which read as an arbitrary choice about
ximni for years. It is not: ximni has no starbase hull and those two maps spawn enemy
stations. Once that is derivable the literal can go.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import races as R
import sbs_utils.procedural.ship_data as SD


DOC = "\n".join([
    "# [Kralien](kralien)",
    "---",
    "Station Prefix: KB",
    "Faces: kralien",
    "Call Sign: KLMNQ",
    "---",
    "The Kralien Union.",
    "",
    "# [Ximni](ximni)",
    "---",
    "Station Prefix: XB",
    "Fleet Scale: 2",
    "---",
    "",
])


class RaceDerivationTests(unittest.TestCase):
    """What the ship table already knows, with nothing declared."""

    def setUp(self):
        R.races_clear()
        SD.ship_data_reset_for_mission()
        SD.get_ship_data()

    def tearDown(self):
        R.races_clear()
        SD.ship_data_reset_for_mission()

    def test_the_stock_races_come_out_of_the_ship_table(self):
        found = R.race_list()
        for race in ("kralien", "torgoth", "arvonian", "skaraan", "ximni", "pirate"):
            self.assertIn(race, found)

    def test_non_races_are_not_races(self):
        # `monster` is the space monster and `roklithoid` is what asteroids are made of.
        # Both are origins; neither is a people you can fight as a faction.
        found = R.race_list()
        self.assertNotIn("monster", found)
        self.assertNotIn("roklithoid", found)

    def test_the_station_hull_each_map_hardcodes_is_derivable(self):
        # These four literals are what borderwar and deepstrike carry in their if-chains.
        self.assertEqual("starbase_kralien", R.race_station_hull("kralien"))
        self.assertEqual("starbase_torgoth", R.race_station_hull("torgoth"))
        self.assertEqual("starbase_arvonian", R.race_station_hull("arvonian"))
        self.assertEqual("starbase_skaraan", R.race_station_hull("skaraan"))

    def test_a_race_without_a_station_says_so(self):
        """The reason borderwar and deepstrike list three races and not four.

        Neither ximni nor pirate has a starbase hull, and those two maps build enemy
        stations. The shortened literal was encoding this constraint by hand.
        """
        self.assertIsNone(R.race_station_hull("ximni"))
        self.assertIsNone(R.race_station_hull("pirate"))
        self.assertFalse(R.race_has_station("ximni"))
        self.assertTrue(R.race_has_station("kralien"))

    def test_hull_counts_ignore_stations_and_do_not_filter_on_the_ship_role(self):
        # arvonian_fighter is `cockpit,fighter` and carries no `ship` role, so a role
        # filter would drop it - the mistake `_side_split` exists to avoid.
        self.assertIn("arvonian_fighter", R.race_hulls("arvonian"))
        self.assertNotIn("starbase_arvonian", R.race_hulls("arvonian"))
        self.assertEqual(len(R.race_hulls("arvonian")), R.race_hull_count("arvonian"))

    def test_case_and_spacing_do_not_matter(self):
        self.assertEqual("starbase_kralien", R.race_station_hull("  KRALIEN "))
        self.assertTrue(R.race_exists("Kralien"))

    def test_an_unknown_race_answers_empty_rather_than_raising(self):
        self.assertEqual([], R.race_hulls("nosuchrace"))
        self.assertIsNone(R.race_station_hull("nosuchrace"))
        self.assertFalse(R.race_exists("nosuchrace"))


class NoShipTableTests(unittest.TestCase):
    """"Nothing is loaded" must answer empty WITHOUT forcing a load."""

    def setUp(self):
        R.races_clear()
        SD.ship_data_reset_for_mission()

    def tearDown(self):
        SD.ship_data_reset_for_mission()

    def test_asking_a_question_does_not_load_the_ship_table(self):
        """Counting hulls must not flip `ship_data_is_loaded`.

        That probe is how the depth guard tells "this roster is too thin" from "I cannot
        judge yet". A count that loaded the table to answer would make the guard report
        every roster the first time anything asked.
        """
        self.assertFalse(SD.ship_data_is_loaded())
        self.assertEqual([], R.race_list())
        self.assertEqual(0, R.race_hull_count("kralien"))
        self.assertIsNone(R.race_station_hull("kralien"))
        self.assertFalse(SD.ship_data_is_loaded(), "answering must not force a load")


class RaceOverrideTests(unittest.TestCase):
    """Declaring is for the four things the ship table cannot say."""

    def setUp(self):
        R.races_clear()
        SD.ship_data_reset_for_mission()
        SD.get_ship_data()
        R.race_declare_text(DOC)

    def tearDown(self):
        R.races_clear()
        SD.ship_data_reset_for_mission()

    def test_declared_fields_are_read(self):
        self.assertEqual("KB", R.race_station_prefix("kralien"))
        self.assertEqual("kralien", R.race_faces("kralien"))
        self.assertEqual("KLMNQ", R.race_call_sign("kralien"))
        self.assertEqual(2.0, R.race_fleet_scale("ximni"))

    def test_an_undeclared_race_still_answers_usefully(self):
        # Absent means derived, not broken. A prefix is invented rather than left empty,
        # because a station called " 1" is worse than "TOB 1".
        self.assertEqual("TOB", R.race_station_prefix("torgoth"))
        self.assertEqual("torgoth", R.race_faces("torgoth"))
        self.assertIsNone(R.race_call_sign("torgoth"))
        self.assertEqual(1.0, R.race_fleet_scale("torgoth"))

    def test_a_declaration_never_invents_a_station(self):
        # ximni declares a prefix but has no station hull. Declaring one field must not
        # make the race look station-capable to the maps that filter on it.
        self.assertEqual("XB", R.race_station_prefix("ximni"))
        self.assertFalse(R.race_has_station("ximni"))

    def test_an_explicit_station_hull_overrides_the_derived_one(self):
        R.race_declare_text("# [Kralien](kralien)\n---\nStation Hull: starbase_civil\n---\n")
        self.assertEqual("starbase_civil", R.race_station_hull("kralien"))

    def test_redeclaring_replaces(self):
        R.race_declare_text("# [Kralien](kralien)\n---\nStation Prefix: ZZ\n---\n")
        self.assertEqual("ZZ", R.race_station_prefix("kralien"))

    def test_an_unknown_field_is_named(self):
        # A dropped field reads as accepted and changes nothing - the silent-no-op shape.
        import contextlib, io as _io
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            R.race_declare_text("# [Kralien](kralien)\n---\nStation Prefx: KB\n---\n")
        self.assertIn("station_prefx", buf.getvalue())

    def test_clear_empties_the_registry(self):
        self.assertTrue(R.races_count() > 0)
        R.races_clear()
        self.assertEqual(0, R.races_count())
        # Overrides go; the DERIVED facts are unaffected, because they were never stored.
        self.assertEqual("starbase_kralien", R.race_station_hull("kralien"))


class NpcListTests(unittest.TestCase):
    """The roster a map spawns from: in the table, enabled, and with a fleet ladder."""

    def setUp(self):
        R.races_clear()
        SD.ship_data_reset_for_mission()
        SD.get_ship_data()
        from sbs_utils.procedural import fleet_tables as FT
        FT.fleet_tables_reset()
        self.FT = FT

    def tearDown(self):
        self.FT.fleet_tables_reset()
        SD.ship_data_reset_for_mission()

    def test_a_race_with_no_fleet_ladder_cannot_raid(self):
        # Every gate is invisible on its own: a race with no ladder makes fleet_create
        # print and return None, which reads as "the mission has no enemies".
        self.assertEqual([], R.race_npc_list())
        self.FT.fleet_table_register("kralien", [[["kralien_cruiser"]]])
        self.assertEqual(["kralien"], R.race_npc_list())

    def test_the_npc_races_setting_still_gates(self):
        from sbs_utils.procedural.settings import settings_get_defaults
        self.FT.fleet_table_register("kralien", [[["kralien_cruiser"]]])
        self.FT.fleet_table_register("torgoth", [[["torgoth_goliath"]]])
        settings = settings_get_defaults()
        keep = settings.get("NPC_RACES")
        settings["NPC_RACES"] = "Kralien"
        try:
            self.assertEqual(["kralien"], R.race_npc_list())
        finally:
            settings["NPC_RACES"] = keep


if __name__ == "__main__":
    unittest.main()
