"""A mission can read how it was launched.

Engine 1.3.5 added exe arguments (`autostartserver`, `defaultmission=`) plus two script
commands to read them. The shapes below are MEASURED against that engine, via the
`cli_probe` mission, not guessed:

    Artemis3-x64-release.exe autostartserver defaultmission=cli_probe map=test_all bareflag

    command_line_list() -> [exe, 'autostartserver', 'defaultmission=cli_probe',
                            'map=test_all', 'bareflag']
    command_line_dict() -> {'defaultmission': 'cli_probe', 'map': 'test_all'}

Two facts these tests pin down, because the whole automation story rests on them: an
UNRECOGNIZED `key=value` argument survives to the dict (so a mission can define its own),
and a BARE flag never reaches the dict (so presence switches need the list).

The degrade-to-empty tests matter as much as the happy path. A mission has to run
identically when launched by hand and under cosmos_dev, where there is no engine command
line at all - a mission that raises because nobody passed `map=` is worse than useless.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (settle node import order)
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.command_line import (
    command_line_dict, command_line_get, command_line_has, command_line_list,
    command_line_mission_changed)


class _FakeSbs:
    """Mimics the engine's two commands. Shapes copied from the measured output."""

    def __init__(self, args=None, missing=False, raises=False):
        self._args = list(args or [])
        self._missing = missing
        self._raises = raises

    def __getattr__(self, name):
        # An engine older than 1.3.5 simply does not have these.
        if self._missing and name in ("command_line_list", "command_line_dict"):
            raise AttributeError(name)
        raise AttributeError(name)

    def command_line_list(self):
        if self._missing:
            raise AttributeError("command_line_list")
        if self._raises:
            raise RuntimeError("engine said no")
        return ["C:/cosmos/Artemis3-x64-release.exe"] + self._args

    def command_line_dict(self):
        if self._missing:
            raise AttributeError("command_line_dict")
        if self._raises:
            raise RuntimeError("engine said no")
        out = {}
        for arg in self._args:
            if "=" in arg:
                k, _, v = arg.partition("=")
                out[k] = v
        return out


class _Ctx:
    def __init__(self, sbs):
        self.sbs = sbs


class _WithArgs(unittest.TestCase):
    ARGS = ["autostartserver", "defaultmission=cli_probe", "map=test_all", "bareflag"]
    # The measured run WAS cli_probe, so the fixture says so. It matters now: a
    # mission-scoped argument reads as absent once we are running a DIFFERENT mission
    # from the one `defaultmission=` names - see TestMissionScope below.
    MISSION = "cli_probe"

    def setUp(self):
        self._saved = FrameContext.context
        FrameContext.context = _Ctx(_FakeSbs(self.ARGS))
        from sbs_utils import fs
        self._saved_mission = fs.mission_name
        fs.mission_name = self.MISSION

    def tearDown(self):
        from sbs_utils import fs
        fs.mission_name = self._saved_mission
        FrameContext.context = self._saved


class TestReading(_WithArgs):
    def test_the_list_carries_everything_including_the_exe(self):
        args = command_line_list()
        self.assertTrue(args[0].endswith(".exe"))
        self.assertIn("autostartserver", args)
        self.assertIn("map=test_all", args)

    def test_the_dict_carries_only_key_value(self):
        self.assertEqual(command_line_dict(),
                         {"defaultmission": "cli_probe", "map": "test_all"})

    def test_an_unrecognized_key_value_survives(self):
        """The whole automation story: `map=` is not an engine flag and still arrives, so a
        mission can define launch arguments the engine knows nothing about."""
        self.assertEqual(command_line_get("map"), "test_all")

    def test_a_bare_flag_never_reaches_the_dict(self):
        self.assertNotIn("autostartserver", command_line_dict())
        self.assertNotIn("bareflag", command_line_dict())
        self.assertTrue(command_line_has("autostartserver"))
        self.assertTrue(command_line_has("bareflag"))

    def test_lookup_is_case_and_space_insensitive(self):
        """A launch argument is typed by a person; `Map=` must not behave differently."""
        self.assertEqual(command_line_get("MAP"), "test_all")
        self.assertEqual(command_line_get("  map  "), "test_all")
        self.assertTrue(command_line_has("AutoStartServer"))

    def test_a_missing_key_returns_the_default(self):
        self.assertIsNone(command_line_get("nope"))
        self.assertEqual(command_line_get("nope", "fallback"), "fallback")
        self.assertFalse(command_line_has("nope"))

    def test_the_exe_path_cannot_match_a_flag(self):
        FrameContext.context = _Ctx(_FakeSbs(["x"]))
        FrameContext.context.sbs._args = []
        # exe is index 0 and must be skipped
        self.assertFalse(command_line_has("C:/cosmos/Artemis3-x64-release.exe"))


class TestDegrading(unittest.TestCase):
    """A mission must behave identically with no engine command line at all."""

    def setUp(self):
        self._saved = FrameContext.context

    def tearDown(self):
        FrameContext.context = self._saved

    def _expect_empty(self, why):
        self.assertEqual(command_line_list(), [], why)
        self.assertEqual(command_line_dict(), {}, why)
        self.assertIsNone(command_line_get("map"), why)
        self.assertEqual(command_line_get("map", "d"), "d", why)
        self.assertFalse(command_line_has("autostartserver"), why)

    def test_no_frame_context(self):
        FrameContext.context = None
        self._expect_empty("outside a frame - import time, tests")

    def test_engine_older_than_1_3_5(self):
        FrameContext.context = _Ctx(_FakeSbs(missing=True))
        self._expect_empty("an engine that predates the commands")

    def test_engine_raises(self):
        FrameContext.context = _Ctx(_FakeSbs(["map=x"], raises=True))
        self._expect_empty("the command exists but blew up")


class TestMockMatchesEngine(unittest.TestCase):
    """The mock's shapes must match the measured engine, or headless proves nothing."""

    def setUp(self):
        import cosmos_dev.mock.sbs as mock
        self.mock = mock
        self._saved = list(mock.command_line_list())

    def tearDown(self):
        self.mock.set_command_line(self._saved[1:])

    def test_empty_by_default_but_still_has_an_exe(self):
        self.mock.set_command_line([])
        self.assertEqual(len(self.mock.command_line_list()), 1)
        self.assertEqual(self.mock.command_line_dict(), {})

    def test_same_split_as_the_engine(self):
        self.mock.set_command_line(
            ["autostartserver", "defaultmission=cli_probe", "map=test_all", "bareflag"])
        self.assertEqual(self.mock.command_line_dict(),
                         {"defaultmission": "cli_probe", "map": "test_all"})
        self.assertIn("autostartserver", self.mock.command_line_list())

    def test_the_library_reads_the_mock(self):
        self.mock.set_command_line(["map=peacetime"])
        saved = FrameContext.context
        FrameContext.context = _Ctx(self.mock)
        try:
            self.assertEqual(command_line_get("map"), "peacetime")
        finally:
            FrameContext.context = saved


class TestMastCanCallThem(unittest.TestCase):
    """A module invisible to MAST cannot be used by a mission - the failure is a NameError
    in the engine, which headless tests do not catch."""

    def test_registered(self):
        import sys
        import cosmos_dev.mock.sbs as mock
        sys.modules.setdefault("sbs", mock)
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        from sbs_utils.mast.mast_globals import MastGlobals
        for name in ("command_line_list", "command_line_dict",
                     "command_line_get", "command_line_has"):
            self.assertIn(name, MastGlobals.globals,
                          f"{name} is not MAST-callable - add its module to "
                          "mast_sbs/mast_sbs_procedural.py")


class TestMissionScope(_WithArgs):
    """`run_next_mission` swaps the mission but not argv.

    So `profile=`, `map=`, `console=` and `var.NAME=` - which all describe ONE mission -
    must stop applying once we have switched to another. `seed=`, `run=`, `record=` and
    `test=` describe the launch and keep applying.

    `defaultmission=` is the only baseline there can be: the engine forks a fresh process
    per mission, so nothing held in memory survives to say what we started as.
    """

    ARGS = ["autostartserver", "defaultmission=cli_probe", "map=test_all",
            "profile=soak", "console=helm", "var.DIFFICULTY=3", "seed=7", "run=a"]

    def _switch_to(self, mission):
        from sbs_utils import fs
        fs.mission_name = mission

    def test_the_launched_mission_keeps_everything(self):
        self.assertFalse(command_line_mission_changed())
        self.assertEqual(command_line_get("profile"), "soak")
        self.assertEqual(command_line_get("map"), "test_all")

    def test_another_mission_drops_the_mission_scoped_ones(self):
        self._switch_to("something_else")
        self.assertTrue(command_line_mission_changed())
        for key in ("profile", "map", "console"):
            self.assertIsNone(command_line_get(key), key)
        self.assertNotIn("var.DIFFICULTY", command_line_dict())

    def test_another_mission_keeps_the_launch_scoped_ones(self):
        self._switch_to("something_else")
        self.assertEqual(command_line_get("seed"), "7")
        self.assertEqual(command_line_get("run"), "a")
        self.assertEqual(command_line_dict()["defaultmission"], "cli_probe")

    def test_the_list_is_never_filtered(self):
        """command_line_has() reads the raw argv for bare flags; nothing there is
        mission-scoped, and rewriting history would be its own trap."""
        self._switch_to("something_else")
        self.assertIn("profile=soak", command_line_list())
        self.assertTrue(command_line_has("autostartserver"))

    def test_no_baseline_means_no_scoping(self):
        """Fail-safe. Launched from the menu, or on an engine that does not pass
        defaultmission= through, this must not engage at all."""
        FrameContext.context = _Ctx(_FakeSbs(["map=test_all", "profile=soak"]))
        self._switch_to("something_else")
        self.assertFalse(command_line_mission_changed())
        self.assertEqual(command_line_get("profile"), "soak")

    def test_case_and_path_do_not_read_as_a_switch(self):
        """A person types the folder name. Reading `Cli_Probe` as a different mission
        would drop a profile on the very first run."""
        self._switch_to("CLI_Probe")
        self.assertFalse(command_line_mission_changed())
        FrameContext.context = _Ctx(_FakeSbs(["defaultmission=missions/cli_probe"]))
        self._switch_to("cli_probe")
        self.assertFalse(command_line_mission_changed())


if __name__ == "__main__":
    unittest.main()
