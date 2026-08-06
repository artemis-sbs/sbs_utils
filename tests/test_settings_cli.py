"""Launch arguments reach the settings, and a typo says so.

Engine 1.3.5 passes unrecognized `key=value` arguments through to `command_line_dict()`,
so a mission defines its own without any engine involvement. Two surfaces, deliberately
different in kind:

    profile=<name>     names a FILE - profiles/<name>.yaml - for bulk config
    var.NAME=value     one override, for deltas

The split is the point. `cmd.exe` caps a command line at 8191 characters, shortcuts
truncate it, Windows quoting around spaces and `=` is painful, and none of it is typed,
commented, diffable or reviewable. A file is all of those. So the command line NAMES the
configuration rather than carrying it.

Precedence, lowest to highest::

    built-in defaults < settings.yaml < profile= < COSMOS_SETTINGS env < var.NAME=

`var.` last because typing it is the most explicit per-launch act there is.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (settle node import order)
import cosmos_dev.mock.sbs as mock
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural import settings as S


class _Ctx:
    sbs = mock


class _Base(unittest.TestCase):
    def setUp(self):
        self._saved_ctx = FrameContext.context
        self._saved_env = os.environ.pop("COSMOS_SETTINGS", None)
        FrameContext.context = _Ctx()
        mock.set_command_line([])
        S.setting_defaults = None          # the merge is cached; each test re-merges
        self._warnings = []
        from sbs_utils.procedural import execution
        self._real_log = execution.log
        execution.log = lambda m, *a, **k: self._warnings.append(m)

    def tearDown(self):
        from sbs_utils.procedural import execution
        execution.log = self._real_log
        FrameContext.context = self._saved_ctx
        mock.set_command_line([])
        S.setting_defaults = None
        os.environ.pop("COSMOS_SETTINGS", None)
        if self._saved_env is not None:
            os.environ["COSMOS_SETTINGS"] = self._saved_env


class TestVarOverrides(_Base):
    def test_a_flat_setting_is_overridden(self):
        mock.set_command_line(["var.DIFFICULTY=9"])
        self.assertEqual(S.settings_get_defaults()["DIFFICULTY"], 9)

    def test_the_value_gets_a_sensible_type(self):
        """A command-line value is always a string; ints must not arrive as '9'."""
        mock.set_command_line(["var.DIFFICULTY=9", "var.AUTO_START=true",
                               "var.MAP_SIZE=Large", "var.AUTO_START_DELAY=2.5"])
        s = S.settings_get_defaults()
        self.assertEqual(s["DIFFICULTY"], 9)
        self.assertIs(s["AUTO_START"], True)
        self.assertEqual(s["MAP_SIZE"], "Large")
        self.assertEqual(s["AUTO_START_DELAY"], 2.5)

    def test_a_nested_setting_via_a_dotted_path(self):
        """The motivating case: turning autoplay on from a launch argument. AUTO_PLAY is a
        dict, so a flat key could not reach it."""
        mock.set_command_line(["var.AUTO_PLAY.enable=true"])
        self.assertIs(S.settings_get_defaults()["AUTO_PLAY"]["enable"], True)

    def test_a_nested_override_keeps_its_siblings(self):
        """Setting one key of a dict must not wipe the rest of it."""
        S.setting_defaults = None
        before = dict(S.settings_get_defaults().get("OPERATOR_MODE") or {})
        self.assertIn("pin", before)
        S.setting_defaults = None
        mock.set_command_line(["var.OPERATOR_MODE.enable=true"])
        after = S.settings_get_defaults()["OPERATOR_MODE"]
        self.assertIs(after["enable"], True)
        self.assertEqual(after.get("pin"), before.get("pin"),
                         "a dotted override replaced the whole dict instead of merging")

    def test_an_unknown_name_warns_but_still_applies(self):
        """Applied because a mission may read a setting sbs_utils never heard of; warned
        because `var.DIFFICULTLY=7` would otherwise look like it worked."""
        mock.set_command_line(["var.DIFFICULTLY=7"])
        s = S.settings_get_defaults()
        self.assertEqual(s["DIFFICULTLY"], 7)
        self.assertTrue(any("DIFFICULTLY" in w for w in self._warnings), self._warnings)

    def test_a_known_name_is_silent(self):
        mock.set_command_line(["var.DIFFICULTY=3"])
        S.settings_get_defaults()
        self.assertEqual(self._warnings, [])

    def test_other_arguments_are_ignored(self):
        mock.set_command_line(["autostartserver", "map=x", "defaultmission=y"])
        s = S.settings_get_defaults()
        self.assertNotIn("map", s)
        self.assertEqual(self._warnings, [])


class TestProfile(_Base):
    def _write_profile(self, name, body):
        from sbs_utils.fs import get_mission_dir
        folder = os.path.join(get_mission_dir(), "profiles")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name + ".yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_a_profile_is_loaded(self):
        self._write_profile("soak", "DIFFICULTY: 11\nMAP_SIZE: Huge\n")
        mock.set_command_line(["profile=soak"])
        s = S.settings_get_defaults()
        self.assertEqual(s["DIFFICULTY"], 11)
        self.assertEqual(s["MAP_SIZE"], "Huge")

    def test_a_missing_profile_warns_rather_than_silently_doing_nothing(self):
        mock.set_command_line(["profile=nope"])
        S.settings_get_defaults()
        self.assertTrue(any("nope" in w for w in self._warnings), self._warnings)

    def test_var_beats_the_profile(self):
        """The command line is for deltas ON TOP of a named configuration."""
        self._write_profile("soak", "DIFFICULTY: 11\n")
        mock.set_command_line(["profile=soak", "var.DIFFICULTY=2"])
        self.assertEqual(S.settings_get_defaults()["DIFFICULTY"], 2)

    def test_var_beats_the_env_override(self):
        os.environ["COSMOS_SETTINGS"] = '{"DIFFICULTY": 4}'
        S.setting_defaults = None
        mock.set_command_line(["var.DIFFICULTY=8"])
        self.assertEqual(S.settings_get_defaults()["DIFFICULTY"], 8)

    def test_the_env_override_still_beats_a_profile(self):
        self._write_profile("soak", "DIFFICULTY: 11\n")
        os.environ["COSMOS_SETTINGS"] = '{"DIFFICULTY": 4}'
        S.setting_defaults = None
        mock.set_command_line(["profile=soak"])
        self.assertEqual(S.settings_get_defaults()["DIFFICULTY"], 4)


class TestNoCommandLine(_Base):
    """A mission must behave identically launched by hand or under cosmos_dev."""

    def test_nothing_passed_changes_nothing(self):
        mock.set_command_line([])
        s = S.settings_get_defaults()
        self.assertEqual(s["DIFFICULTY"], 5)
        self.assertEqual(self._warnings, [])

    def test_no_frame_context_is_survivable(self):
        FrameContext.context = None
        s = S.settings_get_defaults()
        self.assertEqual(s["DIFFICULTY"], 5)


if __name__ == "__main__":
    unittest.main()
