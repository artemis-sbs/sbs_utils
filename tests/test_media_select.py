"""Choosing music, now that a skybox no longer chooses it for you.

Every `@media/skybox` label used to end in `if client_id==0: music_schedule_random()`,
because scheduling a skybox runs its body and nothing else ever picked a track. This
pins the machinery that replaced it: a discoverable list, one shared spec matcher, a
selection that warns when it matches nothing, and a mod tier in the settings that a
mission can still outrank.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import sbs_utils.mast_sbs.story_nodes  # register node types
from sbs_utils.mast_sbs.story_nodes.media import MediaLabel
from sbs_utils.procedural import media
from sbs_utils.procedural import settings as settings_mod
from sbs_utils.helpers import FrameContext


def _label(kind, path, display_name, if_exp=None):
    """A media label, built the way the compiler builds one."""
    return MediaLabel(kind, path, display_name, if_exp=if_exp, loc=0)


class MediaListTest(unittest.TestCase):
    def setUp(self):
        MediaLabel.clear()
        media.music_reset()
        FrameContext.task = None

    def tearDown(self):
        MediaLabel.clear()
        media.music_reset()
        FrameContext.task = None

    def test_only_banks_that_exist_are_listed(self):
        """A label whose folder is missing is not offered - the dropdown must never
        show something scheduling would refuse."""
        _label("music", "default", "Cosmos Default Music")
        _label("music", "Artemis2", "Classic Artemis2 music")
        _label("music", "no_such_bank", "Ghost")
        self.assertEqual([m.path for m in media.music_get_list()],
                         ["default", "artemis2"])

    def test_a_conditional_label_does_not_crash_the_list(self):
        """THE REGRESSION. `get_of_type` took a required `task` and every caller passed
        None, so a label carrying an `if` raised AttributeError inside the schedule.
        No shipped label used the form, which is why it never bit.

        With no task there is nothing to evaluate against, so the condition is skipped
        rather than fatal - an unevaluatable `if` must not delete the label."""
        _label("music", "default", "Cosmos Default Music", if_exp="SOME_UNSET_FLAG")
        self.assertEqual([m.path for m in MediaLabel.get_of_type("music", None)],
                         ["default"])

    def test_a_broken_condition_drops_the_label_not_the_task(self):
        """A mistyped `if` on ONE media label must not end the task building the picker.
        `eval_code_checked` reports and ends by default; the listing path opts out."""
        from sbs_utils.mast.mastscheduler import MastAsyncTask

        class _Task:
            """The REAL eval path, with only the two outcomes stubbed - so this pins how
            eval_code_checked actually behaves, not how a fake believes it behaves."""
            ended = False
            eval_code_checked = MastAsyncTask.eval_code_checked

            def eval_globals(self):
                return {}

            def get_symbols(self):
                return {}

            def runtime_error(self, err):
                raise AssertionError("must not report as fatal")

            def end(self):
                _Task.ended = True

        _label("music", "default", "Cosmos Default Music")
        _label("music", "artemis2", "Classic Artemis2 music", if_exp="NOPE_UNDEFINED")
        got = [m.path for m in MediaLabel.get_of_type("music", _Task())]
        self.assertEqual(got, ["default"])
        self.assertFalse(_Task.ended)

    def test_declaration_order_is_stable(self):
        _label("music", "Artemis2", "Classic Artemis2 music")
        _label("music", "default", "Cosmos Default Music")
        self.assertEqual([m.path for m in media.music_get_list()],
                         ["artemis2", "default"])


class MediaFindTest(unittest.TestCase):
    def setUp(self):
        MediaLabel.clear()
        FrameContext.task = None
        _label("music", "default", "Cosmos Default Music")
        _label("music", "Artemis2", "Classic Artemis2 music")

    def tearDown(self):
        MediaLabel.clear()

    def test_by_index(self):
        self.assertEqual(media.music_find(1).path, "artemis2")
        self.assertEqual(media.music_find("1").path, "artemis2")
        self.assertIsNone(media.music_find(7))

    def test_by_path_ignoring_case(self):
        self.assertEqual(media.music_find("artemis2").path, "artemis2")

    def test_by_display_name(self):
        self.assertEqual(media.music_find("Cosmos Default Music").path, "default")

    def test_by_unique_substring(self):
        self.assertEqual(media.music_find("Artemis2 mus").path, "artemis2")

    def test_ambiguous_returns_none(self):
        """Starting the wrong soundtrack silently is worse than saying nothing matched.
        'music' is a substring of BOTH display names."""
        self.assertIsNone(media.music_find("music"))

    def test_unknown_returns_none(self):
        self.assertIsNone(media.music_find("Artmeis2"))

    def test_it_is_the_same_matcher_maps_use(self):
        """One rule, so `map=siege` and `MUSIC_SELECT=siege` cannot come to mean
        different things."""
        from sbs_utils.procedural.maps import label_find_by_spec
        self.assertIs(media.music_find("artemis2"),
                      label_find_by_spec(media.music_get_list(), "artemis2"))


class BankTest(unittest.TestCase):
    def setUp(self):
        MediaLabel.clear()
        media.music_reset()
        FrameContext.task = None

    def tearDown(self):
        MediaLabel.clear()
        media.music_reset()
        FrameContext.task = None

    def test_nothing_scheduled_reports_the_engine_default(self):
        self.assertEqual(media.music_current(), "default")

    def test_a_stock_bank_has_its_stingers(self):
        self.assertTrue(media.music_bank_has("default", "victory"))
        self.assertTrue(media.music_bank_has("default", "failure"))
        self.assertFalse(media.music_bank_has("default", "not_a_sting"))

    def test_an_unknown_bank_has_nothing(self):
        self.assertFalse(media.music_bank_has("no_such_bank", "victory"))

    def test_a_sting_plays_from_the_selected_bank(self):
        """The point of the whole function: missions hardcoded `music/default/victory`
        ~40 times, so a game scored to another bank still ended on the stock sting."""
        played = []
        self._fake_engine(played)
        media._music_current[0] = "artemis2"
        self.assertTrue(media.music_play_sting("victory"))
        self.assertEqual(played, [(0, "music/artemis2/victory")])

    def test_it_falls_back_per_file_not_per_bank(self):
        """A bank is only conventionally start/main/victory/failure, so a mod's bank may
        ship its own `main` and no `victory`. Losing the mod's whole soundtrack over one
        missing file would be the wrong trade."""
        played = []
        self._fake_engine(played)
        media._music_current[0] = "no_such_bank"
        media.music_play_sting("victory")
        self.assertEqual(played, [(0, "music/default/victory")])

    def test_no_engine_is_silent_not_fatal(self):
        """Music must never be able to end the task telling the story."""
        from sbs_utils.helpers import FrameContext
        saved, FrameContext.context = FrameContext.context, None
        try:
            self.assertFalse(media.music_play_sting("victory"))
        finally:
            FrameContext.context = saved

    def _fake_engine(self, played):
        """Record what reaches sbs.play_music_file, and put it back afterwards."""
        from sbs_utils.helpers import FrameContext, Context, FakeEvent

        class _Sbs:
            @staticmethod
            def play_music_file(ID, filename):
                played.append((ID, filename))

        saved = FrameContext.context
        FrameContext.context = Context(None, _Sbs(), FakeEvent())
        self.addCleanup(lambda: setattr(FrameContext, "context", saved))


class ModDefaultTest(unittest.TestCase):
    """The settings tier a mod needs, which `settings_add_defaults` cannot express."""

    def setUp(self):
        self._saved = settings_mod.setting_defaults
        self._saved_explicit = set(settings_mod._explicit_keys)

    def tearDown(self):
        settings_mod.setting_defaults = self._saved
        settings_mod._explicit_keys = self._saved_explicit

    def test_music_select_has_a_library_default(self):
        settings_mod.setting_defaults = None
        settings_mod._explicit_keys = set()
        self.assertEqual(settings_mod.settings_get_defaults().get("MUSIC_SELECT"),
                         "random")

    def test_a_mod_beats_the_library_builtin(self):
        settings_mod.setting_defaults = {"MUSIC_SELECT": "random"}
        settings_mod._explicit_keys = set()
        self.assertTrue(settings_mod.settings_set_mod_default("MUSIC_SELECT", "TNG_Music"))
        self.assertEqual(settings_mod.setting_defaults["MUSIC_SELECT"], "TNG_Music")

    def test_a_mod_loses_to_what_the_mission_actually_wrote(self):
        settings_mod.setting_defaults = {"MUSIC_SELECT": "Artemis2"}
        settings_mod._explicit_keys = {"MUSIC_SELECT"}
        self.assertFalse(settings_mod.settings_set_mod_default("MUSIC_SELECT", "TNG_Music"))
        self.assertEqual(settings_mod.setting_defaults["MUSIC_SELECT"], "Artemis2")

    def test_add_defaults_still_cannot_do_it(self):
        """Pinning WHY the new tier exists: settings_add_defaults is
        `additions | setting_defaults`, so a key with any value already wins."""
        settings_mod.setting_defaults = {"MUSIC_SELECT": "random"}
        settings_mod._explicit_keys = set()
        settings_mod.settings_add_defaults({"MUSIC_SELECT": "TNG_Music"})
        self.assertEqual(settings_mod.setting_defaults["MUSIC_SELECT"], "random")


if __name__ == "__main__":
    unittest.main()
