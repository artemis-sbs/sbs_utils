"""The engine has to be launched ON the mission, or the devqueue never answers.

`EngineDriver.launch()` used to run the exe bare. The engine then comes up at its main
menu with no mission loaded - and the devqueue lives INSIDE the mission, so every
command times out. The symptom is a 90-second `TimeoutError` that reads like a broken
queue rather than a missing argument, which is exactly the kind of wrong turn that
costs an afternoon.

These pin the argv, not the engine: no exe is ever started.

    python -m unittest tests.test_engine_driver_args
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.engine_driver import driver as D


class FakeProc:
    def poll(self):
        return None


class LaunchArgs(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._popen, self._stop = D.subprocess.Popen, D.EngineDriver.stop_engines
        D.subprocess.Popen = lambda argv, **kw: (self.calls.append(argv), FakeProc())[1]
        D.EngineDriver.stop_engines = staticmethod(lambda: None)
        self.d = D.EngineDriver(r"C:\cosmos", "LM_TestRange")

    def tearDown(self):
        D.subprocess.Popen = self._popen
        D.EngineDriver.stop_engines = self._stop

    def argv(self, **kw):
        self.d.launch(**kw)
        return self.calls[-1]

    def test_it_names_the_mission(self):
        # Without this the engine sits at its menu and nothing is loaded to answer.
        self.assertIn("defaultmission=LM_TestRange", self.argv())

    def test_it_starts_the_server(self):
        self.assertIn("autostartserver", self.argv())

    def test_a_map_is_passed_through(self):
        # `map=` is not an engine flag; it survives to sbs.command_line_dict() for the
        # mission to read, which is what makes an unattended run reach a named map.
        self.assertIn("map=test_all", self.argv(map="test_all"))

    def test_no_map_means_no_map_argument(self):
        self.assertFalse([a for a in self.argv() if a.startswith("map=")])

    def test_autostart_can_be_turned_off(self):
        self.assertNotIn("autostartserver", self.argv(autostart=False))

    def test_explicit_args_replace_everything(self):
        argv = self.argv(args=["justthis"])
        self.assertEqual(argv[1:], ["justthis"])

    def test_the_exe_is_first(self):
        self.assertTrue(self.argv()[0].endswith("Artemis3-x64-release.exe"))
