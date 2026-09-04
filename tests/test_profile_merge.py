"""`profile=a,b` names several profiles and merges them.

One profile per launch made every combination its own file: three house settings and four
mods is twelve files, not seven. A comma list composes them instead - and it used to be
worse than unsupported, because `profile=a,b` looked for a file literally named `a,b.yaml`
and, finding none, applied NEITHER.

What is pinned here is the order (later wins), the content sections accumulating rather
than replacing, and a bad name in the list not taking the good ones down with it.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from sbs_utils.procedural import settings as settings_mod


class ProfileNamesTest(unittest.TestCase):
    def test_one_name_is_one_name(self):
        self.assertEqual(settings_mod._profile_names("soak"), ["soak"])

    def test_a_comma_list_splits_in_typed_order(self):
        self.assertEqual(settings_mod._profile_names("autoplay7,tng_all"),
                         ["autoplay7", "tng_all"])

    def test_spaces_around_a_comma_are_forgiven(self):
        """A launch argument is typed by a person or pasted from a script."""
        self.assertEqual(settings_mod._profile_names(" a , b "), ["a", "b"])

    def test_blank_entries_are_dropped(self):
        self.assertEqual(settings_mod._profile_names("a,,b,"), ["a", "b"])

    def test_a_repeat_is_applied_once(self):
        """Twice is a no-op for settings but would double every include: entry."""
        self.assertEqual(settings_mod._profile_names("a,b,A"), ["a", "b"])


class ProfileMergeTest(unittest.TestCase):
    def test_later_wins_a_settings_key(self):
        merged = settings_mod._profile_merge({"DIFFICULTY": 3, "SEED": 1},
                                             {"DIFFICULTY": 9})
        self.assertEqual(merged, {"DIFFICULTY": 9, "SEED": 1})

    def test_a_key_only_the_earlier_one_set_survives(self):
        merged = settings_mod._profile_merge({"AUTO_START": True}, {"DIFFICULTY": 9})
        self.assertTrue(merged["AUTO_START"])

    def test_include_lists_accumulate_rather_than_replace(self):
        merged = settings_mod._profile_merge(
            {"addons": {"include": ["a28_skyboxes"]}},
            {"addons": {"include": ["debug_tools"]}})
        self.assertEqual(merged["addons"]["include"], ["a28_skyboxes", "debug_tools"])

    def test_exclude_lists_accumulate_too(self):
        merged = settings_mod._profile_merge(
            {"media": {"exclude": ["stock_skies"]}},
            {"media": {"exclude": ["stock_music"]}})
        self.assertEqual(merged["media"]["exclude"], ["stock_skies", "stock_music"])

    def test_an_exclude_and_an_include_do_not_replace_each_other(self):
        """The case a plain `|` got wrong: one profile removes, another adds, both meant."""
        merged = settings_mod._profile_merge(
            {"addons": {"exclude": ["basic_random_skybox"]}},
            {"addons": {"include": ["a28_skyboxes"]}})
        self.assertEqual(merged["addons"]["exclude"], ["basic_random_skybox"])
        self.assertEqual(merged["addons"]["include"], ["a28_skyboxes"])

    def test_a_bare_string_merges_with_a_list(self):
        """Hand-written YAML: `exclude: name` is one entry, not a failed merge."""
        merged = settings_mod._profile_merge(
            {"addons": {"exclude": "one"}}, {"addons": {"exclude": ["two"]}})
        self.assertEqual(merged["addons"]["exclude"], ["one", "two"])

    def test_a_duplicate_entry_is_listed_once(self):
        merged = settings_mod._profile_merge(
            {"addons": {"include": ["a28_skyboxes"]}},
            {"addons": {"include": ["A28_Skyboxes", "debug_tools"]}})
        self.assertEqual(merged["addons"]["include"], ["a28_skyboxes", "debug_tools"])

    def test_a_section_only_one_profile_has_is_kept_whole(self):
        merged = settings_mod._profile_merge(
            {"DIFFICULTY": 3}, {"media": {"include": ["a28"]}})
        self.assertEqual(merged["media"], {"include": ["a28"]})

    def test_a_malformed_section_does_not_raise(self):
        """A profile is hand-written; a bad shape must not fail the launch."""
        merged = settings_mod._profile_merge(
            {"addons": ["not_a_dict"]}, {"addons": {"include": ["a28"]}})
        self.assertEqual(merged["addons"], {"include": ["a28"]})


class ProfileOverridesTest(unittest.TestCase):
    """The whole path, with the two file lookups stubbed out."""

    def setUp(self):
        self._saved_load = settings_mod._profile_load_named
        self._saved_data = settings_mod._profile_data
        self._saved_get = None
        settings_mod._profile_data = None
        self.warnings = []
        self._saved_warn = settings_mod._warn
        settings_mod._warn = lambda m: self.warnings.append(m)
        self._saved_log = settings_mod._log
        settings_mod._log = lambda m: None

    def tearDown(self):
        settings_mod._profile_load_named = self._saved_load
        settings_mod._profile_data = self._saved_data
        settings_mod._warn = self._saved_warn
        settings_mod._log = self._saved_log
        import sbs_utils.procedural.command_line as cl
        if self._saved_get is not None:
            cl.command_line_get = self._saved_get

    def _launch(self, profile_value, files):
        import sbs_utils.procedural.command_line as cl
        self._saved_get = cl.command_line_get
        cl.command_line_get = lambda key, default=None: (
            profile_value if str(key).lower() == "profile" else default)
        settings_mod._profile_load_named = lambda name: files.get(name)

    def test_no_profile_argument_means_no_overrides(self):
        self._launch(None, {})
        self.assertIsNone(settings_mod._profile_overrides())

    def test_two_profiles_merge_later_wins(self):
        self._launch("autoplay7,tng_all",
                     {"autoplay7": {"DIFFICULTY": 7, "AUTO_START": True},
                      "tng_all": {"DIFFICULTY": 3}})
        merged = settings_mod._profile_overrides()
        self.assertEqual(merged["DIFFICULTY"], 3)
        self.assertTrue(merged["AUTO_START"])

    def test_a_missing_name_is_warned_about_and_the_rest_still_apply(self):
        """One typo in a list of two must not discard the other."""
        self._launch("typo,tng_all", {"tng_all": {"DIFFICULTY": 3}})
        merged = settings_mod._profile_overrides()
        self.assertEqual(merged, {"DIFFICULTY": 3})

    def test_every_name_missing_means_no_overrides(self):
        self._launch("typo,alsotypo", {})
        self.assertIsNone(settings_mod._profile_overrides())

    def test_the_cached_profile_is_the_merged_one(self):
        """`settings_profile_addons` reads the cache during COMPILE - it has to see both."""
        self._launch("skies,debug",
                     {"skies": {"addons": {"exclude": ["basic_random_skybox"]}},
                      "debug": {"addons": {"include": ["debug_tools"]}}})
        include, exclude = settings_mod.settings_profile_addons()
        self.assertEqual(include, ["debug_tools"])
        self.assertEqual(exclude, {"basic_random_skybox"})


if __name__ == "__main__":
    unittest.main()
