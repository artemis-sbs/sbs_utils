"""RACE_ART / ART_KEYS re-point a mission's ART faction, never its diplomatic side.

Overriding a STOCK ship key with mod art works on the server and never on a client: the
client resolves a key it already knows against its own data/shipData.yaml, so its stock
artfileroot wins. Pointing the LOOKUP at the mod's own keys is what reaches clients. These
two helpers are that hook, and the thing they must never do is move what side a ship is on.

    python -m unittest tests.test_art_faction_map
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural import ship_data as SD


class _Settings:
    """Stand-in for settings_get_defaults(), so a test never edits real settings."""

    def __init__(self, values):
        self.values = values

    def __call__(self):
        return self.values


class ArtFactionMapTests(unittest.TestCase):

    def setUp(self):
        self._real = SD.filter_ship_data_by_side
        self._real_get = SD.get_ship_data_for
        import sbs_utils.procedural.settings as S
        self._real_settings = S.settings_get_defaults
        self._set({})

    def tearDown(self):
        SD.filter_ship_data_by_side = self._real
        SD.get_ship_data_for = self._real_get
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = self._real_settings

    def _set(self, values):
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = _Settings(values)

    # --- identity: an unset map must change nothing --------------------------

    def test_no_setting_returns_the_race_unchanged(self):
        self.assertEqual("kralien", SD.art_faction_for("kralien"))

    def test_empty_map_returns_the_race_unchanged(self):
        self._set({"RACE_ART": {}})
        self.assertEqual("kralien", SD.art_faction_for("kralien"))

    def test_a_non_dict_setting_is_ignored_rather_than_raising(self):
        self._set({"RACE_ART": "kralien: Cardassian"})
        self.assertEqual("kralien", SD.art_faction_for("kralien"))

    def test_unmapped_race_is_unchanged(self):
        self._set({"RACE_ART": {"kralien": "Cardassian"}})
        self.assertEqual("torgoth", SD.art_faction_for("torgoth"))

    def test_none_and_empty_pass_through(self):
        self.assertIsNone(SD.art_faction_for(None))
        self.assertEqual("", SD.art_faction_for(""))

    # --- mapping -------------------------------------------------------------

    def test_mapped_race_is_replaced(self):
        self._set({"RACE_ART": {"kralien": "Cardassian"}})
        self.assertEqual("Cardassian", SD.art_faction_for("kralien"))

    def test_lookup_is_case_insensitive_on_the_setting_key(self):
        self._set({"RACE_ART": {"KrAlIeN": "Cardassian"}})
        self.assertEqual("Cardassian", SD.art_faction_for("kralien"))

    def test_mapping_a_race_to_itself_is_identity(self):
        self._set({"RACE_ART": {"kralien": "Kralien"}})
        self.assertEqual("kralien", SD.art_faction_for("kralien"))

    # --- the role guard ------------------------------------------------------

    def test_mapping_is_dropped_when_the_target_has_no_hulls_for_that_role(self):
        # Spawning nothing is far harder to notice than wrong art, so a mapping that
        # cannot satisfy the role must fall back rather than win.
        self._set({"RACE_ART": {"kralien": "Cardassian"}})
        SD.filter_ship_data_by_side = lambda *a, **k: []
        self.assertEqual("kralien", SD.art_faction_for("kralien", role="station"))

    def test_mapping_is_kept_when_the_target_has_hulls_for_that_role(self):
        self._set({"RACE_ART": {"kralien": "Cardassian"}})
        SD.filter_ship_data_by_side = lambda *a, **k: ["tng_crd_galor"]
        self.assertEqual("Cardassian", SD.art_faction_for("kralien", role="ship"))

    def test_without_a_role_the_mapping_is_not_checked(self):
        self._set({"RACE_ART": {"kralien": "Cardassian"}})
        SD.filter_ship_data_by_side = lambda *a, **k: []
        self.assertEqual("Cardassian", SD.art_faction_for("kralien"))


class ArtKeyMapTests(unittest.TestCase):

    def setUp(self):
        self._real_get = SD.get_ship_data_for
        import sbs_utils.procedural.settings as S
        self._real_settings = S.settings_get_defaults
        S.settings_get_defaults = _Settings({})

    def tearDown(self):
        SD.get_ship_data_for = self._real_get
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = self._real_settings

    def _set(self, values):
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = _Settings(values)

    def test_no_setting_returns_the_key_unchanged(self):
        self.assertEqual("starbase_command", SD.art_key_for("starbase_command"))

    def test_mapped_key_is_replaced_when_the_replacement_exists(self):
        self._set({"ART_KEYS": {"starbase_command": "tng_fed_starbase"}})
        SD.get_ship_data_for = lambda k: {"key": k}
        self.assertEqual("tng_fed_starbase", SD.art_key_for("starbase_command"))

    def test_replacement_missing_from_the_table_falls_back_to_stock(self):
        # A half-written map should degrade to stock art, never to no station at all.
        self._set({"ART_KEYS": {"starbase_command": "tng_typo"}})
        SD.get_ship_data_for = lambda k: None
        self.assertEqual("starbase_command", SD.art_key_for("starbase_command"))

    def test_none_passes_through(self):
        self.assertIsNone(SD.art_key_for(None))


if __name__ == "__main__":
    unittest.main()
