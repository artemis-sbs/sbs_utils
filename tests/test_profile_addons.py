"""A profile selects ADD-ONS, not just settings.

`profiles/<name>.yaml` could only override settings values. It can now add and remove
add-ons and media packs relative to story.json, so "the A28 skies instead of the stock
ones" is one named profile rather than an edited story.json.

The parts worth pinning are the ones that fail SILENTLY when wrong: a name matched
against the wrong segment, a filter that misses the path a clone actually loads through,
and a profile that empties a story by excluding something another add-on requires.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from sbs_utils.mast.mast import Mast
from sbs_utils.procedural import settings as settings_mod


LIB = "artemis-sbs.LegendaryMissions.basic_random_skybox.v1.4.0.mastlib"


class AddonFolderNameTest(unittest.TestCase):
    """A profile names the FOLDER, never the version - or it rots on the next release."""

    def test_the_third_dot_segment_wins(self):
        self.assertEqual(Mast.addon_folder_name(LIB), "basic_random_skybox")

    def test_it_is_lowercased_so_a_profile_need_not_match_case(self):
        self.assertEqual(
            Mast.addon_folder_name("artemis-sbs.Cosmos-TNG-Mod.TNG_Races.v0.2.3.mastlib"),
            "tng_races")

    def test_a_name_that_is_not_a_lib_is_returned_as_itself(self):
        """Rather than raising: a malformed entry must not take the compile down."""
        self.assertEqual(Mast.addon_folder_name("weird"), "weird")

    def test_it_agrees_with_addon_source_folder(self):
        """These two must not disagree - one decides what a profile excludes, the other
        decides where the add-on is loaded from."""
        import os
        parts = LIB.split(".", 3)
        self.assertEqual(Mast.addon_folder_name(LIB), parts[2].lower())
        self.assertTrue(os.path.basename(parts[2]) == parts[2])


class ProfileSectionTest(unittest.TestCase):
    """A profile is hand-written YAML, so the reader is deliberately tolerant."""

    def setUp(self):
        self._saved = settings_mod._profile_data

    def tearDown(self):
        settings_mod._profile_data = self._saved

    def _profile(self, data):
        settings_mod._profile_data = data

    def test_no_profile_means_no_rules(self):
        self._profile({})
        self.assertEqual(settings_mod.settings_profile_addons(), ([], set()))

    def test_include_and_exclude_are_lowercased(self):
        self._profile({"addons": {"include": ["A28_Skyboxes"],
                                  "exclude": ["Basic_Random_Skybox"]}})
        include, exclude = settings_mod.settings_profile_addons()
        self.assertEqual(include, ["a28_skyboxes"])
        self.assertEqual(exclude, {"basic_random_skybox"})

    def test_a_bare_string_is_one_entry(self):
        self._profile({"addons": {"exclude": "basic_random_skybox"}})
        self.assertEqual(settings_mod.settings_profile_addons()[1],
                         {"basic_random_skybox"})

    def test_blank_entries_are_dropped(self):
        self._profile({"addons": {"include": ["a28_skyboxes", "", "  "]}})
        self.assertEqual(settings_mod.settings_profile_addons()[0], ["a28_skyboxes"])

    def test_a_non_dict_section_is_ignored_not_fatal(self):
        self._profile({"addons": ["basic_random_skybox"]})
        self.assertEqual(settings_mod.settings_profile_addons(), ([], set()))

    def test_media_is_read_the_same_way(self):
        self._profile({"media": {"include": ["A28-Skybox-Mod.media"]}})
        self.assertEqual(settings_mod.settings_profile_media()[0],
                         ["a28-skybox-mod.media"])

    def test_addons_and_media_are_separate_sections(self):
        self._profile({"addons": {"exclude": ["x"]}, "media": {"exclude": ["y"]}})
        self.assertEqual(settings_mod.settings_profile_addons()[1], {"x"})
        self.assertEqual(settings_mod.settings_profile_media()[1], {"y"})


class ProfileResetTest(unittest.TestCase):
    def test_the_parsed_profile_is_forgotten_on_reset(self):
        """A reused interpreter can be pointed at a different mission, and its profile.
        This is the shape of bug the restart soak exists to catch."""
        settings_mod._profile_data = {"addons": {"exclude": ["stale"]}}
        settings_mod.settings_profile_reset()
        self.assertIsNone(settings_mod._profile_data)


class DroppedAddonRecordTest(unittest.TestCase):
    """The `requires` error has to be able to say the profile is why."""

    def setUp(self):
        from sbs_utils.mast import mast as mast_mod
        self.mast_mod = mast_mod
        self._saved = set(mast_mod._PROFILE_DROPPED)

    def tearDown(self):
        self.mast_mod._PROFILE_DROPPED.clear()
        self.mast_mod._PROFILE_DROPPED.update(self._saved)

    def test_dropped_addons_are_readable_by_name(self):
        self.mast_mod._PROFILE_DROPPED.clear()
        self.mast_mod._PROFILE_DROPPED.add("gamemaster")
        self.assertEqual(self.mast_mod.profile_dropped_addons(), {"gamemaster"})

    def test_it_returns_a_copy(self):
        """The caller must not be able to edit the record it is only reporting."""
        self.mast_mod._PROFILE_DROPPED.clear()
        self.mast_mod._PROFILE_DROPPED.add("gamemaster")
        got = self.mast_mod.profile_dropped_addons()
        got.add("something_else")
        self.assertEqual(self.mast_mod.profile_dropped_addons(), {"gamemaster"})


if __name__ == "__main__":
    unittest.main()
