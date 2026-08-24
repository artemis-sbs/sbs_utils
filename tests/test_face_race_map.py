"""RACE_FACES re-points crew portraits, and is applied inside random_face().

"The comms faces are not using the TNG faces for NPCs" - because the art maps move the
HULL faction and faces come from a different name entirely. Face races are SPECIES
(`human`, `cardassian`); ship-data sides are FACTIONS (`Federation`, `Cardassian`). Feeding
a faction to random_face() matches nothing registered and silently falls back to terran.

Applied inside random_face rather than at call sites: LM alone has four NPC face sites, one
of them in a fleet spawner, and a missed one is indistinguishable from the bug.

    python -m unittest tests.test_face_race_map
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils import faces as F


class _Settings:
    def __init__(self, values):
        self.values = values

    def __call__(self):
        return self.values


class FaceRaceMapTests(unittest.TestCase):

    def setUp(self):
        import sbs_utils.procedural.settings as S
        self._real = S.settings_get_defaults
        self._set({})

    def tearDown(self):
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = self._real

    def _set(self, values):
        import sbs_utils.procedural.settings as S
        S.settings_get_defaults = _Settings(values)

    # --- identity: unset must change nothing -------------------------------

    def test_unset_returns_the_race_unchanged(self):
        self.assertEqual("kralien", F.face_race_mapped("kralien"))

    def test_empty_map_returns_the_race_unchanged(self):
        self._set({"RACE_FACES": {}})
        self.assertEqual("kralien", F.face_race_mapped("kralien"))

    def test_a_non_dict_setting_is_ignored(self):
        self._set({"RACE_FACES": "kralien: cardassian"})
        self.assertEqual("kralien", F.face_race_mapped("kralien"))

    def test_none_and_empty_pass_through(self):
        self.assertIsNone(F.face_race_mapped(None))
        self.assertEqual("", F.face_race_mapped(""))

    # --- mapping ------------------------------------------------------------

    def test_mapped_race_is_replaced(self):
        self._set({"RACE_FACES": {"kralien": "cardassian"}})
        self.assertEqual("cardassian", F.face_race_mapped("kralien"))

    def test_lookup_is_case_insensitive(self):
        self._set({"RACE_FACES": {"KrAlIeN": "cardassian"}})
        self.assertEqual("cardassian", F.face_race_mapped("kralien"))

    def test_unmapped_name_passes_through(self):
        # A player face already named by SPECIES must not be disturbed.
        self._set({"RACE_FACES": {"kralien": "cardassian"}})
        self.assertEqual("human", F.face_race_mapped("human"))

    # --- the reason it lives inside random_face -----------------------------

    def test_random_face_applies_the_map(self):
        self._set({"RACE_FACES": {"kralien": "cardassian"}})
        seen = {}

        def fake(race, role):
            seen["race"] = race
            return "FACE"

        real = F.face_random_registered
        F.face_random_registered = fake
        try:
            self.assertEqual("FACE", F.random_face("kralien"))
        finally:
            F.face_random_registered = real
        self.assertEqual("cardassian", seen["race"],
                         "random_face must map before it looks the race up")

    def test_random_face_still_handles_random(self):
        # The `random` sentinel must survive the mapping step untouched.
        self._set({"RACE_FACES": {"kralien": "cardassian"}})
        self.assertIsNotNone(F.random_face("random"))

    def test_random_face_with_no_race_still_works(self):
        self.assertIsNotNone(F.random_face())


if __name__ == "__main__":
    unittest.main()
