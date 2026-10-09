"""Extra ship data is ON unless the mission turns it off, and that is a SETTING.

It was a hardcoded constant from the 2026-08-27 hot fix until 2026-09-01. The reason
it could not stay one: the right answer depends on the INSTALL, not on the build of
the library. The engine only grew a working extra-ship-data path in v1.3.7, and people
are still running v1.3.4 - where a declared hull never registers, and asking to spawn
one dies inside the engine as `bad allocation`, minutes later, against unrelated code.

So off WAS the default, until 2026-10-09. It is on now (the owner's call: the EVA
exosuit, turrets and relic kits should exist in a mission that never heard of the
setting), and a mission that has to run on a v1.3.4 engine turns it off with
`EXTRA_SHIP_DATA: false` in settings.yaml, a profile, or COSMOS_SETTINGS.

What the default may NOT do is write: `TestTheDefaultNeverWrites`.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.procedural.settings as settings_mod
from sbs_utils.procedural.ship_data import (
    extra_ship_data_enabled, extra_ship_data_force)


class _Settings:
    """Swap the cached settings dict, which is what the gate reads."""

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.saved = settings_mod.setting_defaults
        settings_mod.setting_defaults = dict(self.value)

    def __exit__(self, *a):
        settings_mod.setting_defaults = self.saved


class TestTheDefault(unittest.TestCase):
    def setUp(self):
        extra_ship_data_force(None)
        self.addCleanup(extra_ship_data_force, None)

    def test_a_mission_that_says_nothing_gets_it_ON(self):
        """The default, since 2026-10-09. It was OFF, and a template mission that
        loaded the boarding addon and its media pack still drew its suits as
        shuttles for want of one line in a settings file nobody had."""
        with _Settings({}):
            self.assertTrue(extra_ship_data_enabled())

    def test_the_library_default_itself_is_true(self):
        """Not only the `.get` fallback: the built-in table says so too, and it is
        what a settings screen or a dump shows."""
        saved = settings_mod.setting_defaults
        saved_keys = set(settings_mod._explicit_keys)
        settings_mod.setting_defaults = None
        try:
            got = settings_mod.settings_get_defaults()
            if "EXTRA_SHIP_DATA" not in settings_mod._explicit_keys:
                self.assertIs(got["EXTRA_SHIP_DATA"], True)
        finally:
            settings_mod.setting_defaults = saved
            settings_mod._explicit_keys.clear()
            settings_mod._explicit_keys.update(saved_keys)

    def test_a_mission_can_turn_it_OFF(self):
        """The property that protects a v1.3.4 install, now that it is opt-out."""
        with _Settings({"EXTRA_SHIP_DATA": False}):
            self.assertFalse(extra_ship_data_enabled())

    def test_a_mission_can_turn_it_on(self):
        with _Settings({"EXTRA_SHIP_DATA": True}):
            self.assertTrue(extra_ship_data_enabled())

    def test_a_string_true_reads_as_on(self):
        """YAML gives a bool for a bare `true`, but a hand-edit or COSMOS_SETTINGS
        can hand over a string."""
        for said in ("true", "True", " yes ", "on", "1"):
            with _Settings({"EXTRA_SHIP_DATA": said}):
                self.assertTrue(extra_ship_data_enabled(), said)

    def test_a_QUOTED_false_does_NOT_read_as_on(self):
        """The one that would matter. `bool("false")` is True, so a plain bool() here
        would turn the feature on for someone who wrote it off - and on a v1.3.4
        install that is an engine crash on the first spawn, not a wrong pixel."""
        for said in ("false", "False", "no", "off", "0", ""):
            with _Settings({"EXTRA_SHIP_DATA": said}):
                self.assertFalse(extra_ship_data_enabled(), said)


class TestTheOverride(unittest.TestCase):
    """`extra_ship_data_force` is how the feature's own tests run, and how a caller
    that has to decide before settings exist can."""

    def setUp(self):
        self.addCleanup(extra_ship_data_force, None)

    def test_force_on_beats_a_setting_that_says_off(self):
        with _Settings({"EXTRA_SHIP_DATA": False}):
            extra_ship_data_force(True)
            self.assertTrue(extra_ship_data_enabled())

    def test_force_off_beats_a_setting_that_says_on(self):
        with _Settings({"EXTRA_SHIP_DATA": True}):
            extra_ship_data_force(False)
            self.assertFalse(extra_ship_data_enabled())

    def test_clearing_the_override_hands_control_back(self):
        with _Settings({"EXTRA_SHIP_DATA": True}):
            extra_ship_data_force(False)
            extra_ship_data_force(None)
            self.assertTrue(extra_ship_data_enabled())


class TestTheGateIsActuallyWired(unittest.TestCase):
    """The gate is only worth anything if the loaders read it."""

    def setUp(self):
        self.addCleanup(extra_ship_data_force, None)

    def test_add_extra_declines_while_it_is_off(self):
        """`add_extra` answers False exactly as a missing file did, so no caller sees
        a new shape - that was the point of the original hot fix and still holds."""
        from sbs_utils.procedural.ship_data import add_extra
        extra_ship_data_force(False)
        self.assertFalse(add_extra("no_such_ships", mod="nobody"))

    def test_merge_mod_ship_yaml_declines_while_it_is_off(self):
        """The choke point every mod merge funnels through."""
        from sbs_utils.procedural.ship_data import (
            merge_mod_ship_yaml, get_ship_data_for)
        extra_ship_data_force(False)
        merge_mod_ship_yaml(
            "#ship-list:\n  - key: gate_probe_ship\n    side: tsn\n", "GateTest")
        self.assertIsNone(get_ship_data_for("gate_probe_ship"))


if __name__ == "__main__":
    unittest.main()


class TestItSaysWhenItIsOff(unittest.TestCase):
    """Returning False in SILENCE is how this became somebody else's bug.

    Reported from Gamma with a Q as an IndexError inside ShipPicker. The mod's hulls
    were simply absent, so a race-filtered picker matched nothing and indexed an empty
    list - and nowhere in that chain did anything mention a setting being off. The
    warning is the only place the cause is speakable.
    """

    def setUp(self):
        from sbs_utils.procedural import ship_data
        self.addCleanup(extra_ship_data_force, None)
        ship_data.extra_reset()
        self.addCleanup(ship_data.extra_reset)
        self.said = []
        import sbs_utils.procedural.execution as execution
        self.real_log = execution.log
        execution.log = lambda msg, name=None, level=None: self.said.append(str(msg))
        self.addCleanup(setattr, execution, "log", self.real_log)

    def declined(self):
        from sbs_utils.procedural.ship_data import add_extra
        extra_ship_data_force(False)
        return add_extra("no_such_ships", mod="nobody")

    def test_IT_SAYS_SO(self):
        self.assertFalse(self.declined())
        self.assertTrue(any("EXTRA_SHIP_DATA" in m for m in self.said), self.said)

    def test_it_names_the_setting_that_fixes_it(self):
        """A warning that does not say what to change is a warning nobody acts on."""
        self.declined()
        self.assertTrue(any("EXTRA_SHIP_DATA: true" in m for m in self.said), self.said)

    def test_ONCE_not_once_per_mod(self):
        """Every mod on the ship calls this. One line is information; twelve is noise
        that buries the rest of the log."""
        for _ in range(5):
            self.declined()
        self.assertEqual(sum(1 for m in self.said if "EXTRA_SHIP_DATA" in m), 1)

    def test_but_the_next_mission_is_told_again(self):
        """The latch is per MISSION. cosmos_dev reuses one interpreter across
        `run_next_mission` while the engine forks a fresh process, so a latch nothing
        resets goes quiet from run 2 on - and the run that needs the warning is
        whichever one the player is actually on."""
        from sbs_utils.procedural import ship_data
        self.declined()
        ship_data.extra_reset()
        self.declined()
        self.assertEqual(sum(1 for m in self.said if "EXTRA_SHIP_DATA" in m), 2)

    def test_and_it_stays_quiet_when_the_feature_is_ON(self):
        from sbs_utils.procedural.ship_data import add_extra
        extra_ship_data_force(True)
        add_extra("no_such_ships", mod="nobody")
        self.assertFalse([m for m in self.said if "EXTRA_SHIP_DATA is off" in m])


class TestTheDefaultNeverWrites(unittest.TestCase):
    """ON by default must not mean a file appears in a mission that asked for nothing.

    Found the first time the setting was on for LM_TestRange: three of its probe maps
    call the superseded `ship_data_merge_mod` at story top level, `sim_create()` flushed
    what they declared, and the mission's TRACKED `extraShipData.json` was rewritten with
    a `.bak` left beside it. With the default off that route was inert, so nothing had
    ever shown it. The default being on must change nothing there: the generated-file
    route runs when the setting is WRITTEN DOWN, and only then.
    """

    HAND = '{"#ship-list": [{"key": "hand_made_ship", "side": "TSN"}]}\n'
    MOD = ('{"#ship-list": [{"key": "default_probe_ship", "name": "Probe", '
           '"side": "TSN", "artfileroot": "tsn_light_cruiser"}]}')

    def setUp(self):
        import os
        import tempfile
        from sbs_utils.procedural import ship_data, ship_data_mod
        self.sd, self.sdm = ship_data, ship_data_mod
        extra_ship_data_force(None)
        self.addCleanup(extra_ship_data_force, None)
        self.saved_cache = ship_data.ship_data_cache
        ship_data.ship_data_cache = {"#ship-list": []}
        self.addCleanup(setattr, ship_data, "ship_data_cache", self.saved_cache)
        self.addCleanup(ship_data.reset_ship_data_caches)
        ship_data_mod.ship_data_mod_reset()
        self.addCleanup(ship_data_mod.ship_data_mod_reset)
        saved_keys = set(settings_mod._explicit_keys)
        settings_mod._explicit_keys.discard("EXTRA_SHIP_DATA")

        def _restore():
            settings_mod._explicit_keys.clear()
            settings_mod._explicit_keys.update(saved_keys)
        self.addCleanup(_restore)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name
        self.path = os.path.join(self.dir, ship_data_mod.EXTRA_SHIP_DATA)
        self.said = []
        import sbs_utils.procedural.execution as execution
        real_log = execution.log
        execution.log = lambda msg, name=None, level=None: self.said.append(str(msg))
        self.addCleanup(setattr, execution, "log", real_log)

    def files(self):
        import os
        return sorted(os.listdir(self.dir))

    def test_on_by_default_is_not_ASKED(self):
        with _Settings({}):
            self.assertTrue(extra_ship_data_enabled())
            self.assertFalse(self.sd.extra_ship_data_asked())

    def test_written_down_is_asked(self):
        settings_mod._explicit_keys.add("EXTRA_SHIP_DATA")
        with _Settings({"EXTRA_SHIP_DATA": True}):
            self.assertTrue(self.sd.extra_ship_data_asked())

    def test_written_down_FALSE_is_neither(self):
        settings_mod._explicit_keys.add("EXTRA_SHIP_DATA")
        with _Settings({"EXTRA_SHIP_DATA": False}):
            self.assertFalse(extra_ship_data_enabled())
            self.assertFalse(self.sd.extra_ship_data_asked())

    def test_the_default_writes_NOTHING_into_the_mission_folder(self):
        """The LM_TestRange case, exactly: a hand-authored file is there, a probe
        declares a hull through the generated-file route, and the sim is created."""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(self.HAND)
        with _Settings({}):
            self.assertEqual(self.sdm.ship_data_merge_mod(self.MOD, "Probe"), 0)
            self.assertEqual(self.sdm.ship_data_pending_count(), 0)
            self.assertIsNone(self.sdm.ship_data_flush_mod_file(self.dir))
        self.assertEqual(self.files(), [self.sdm.EXTRA_SHIP_DATA], "no .bak, no .tmp")
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.HAND)

    def test_and_it_says_why_ONCE(self):
        with _Settings({}):
            for _ in range(3):
                self.sdm.ship_data_merge_mod(self.MOD, "Probe")
        said = [m for m in self.said if "ship_data_merge_mod" in m]
        self.assertEqual(len(said), 1, self.said)
        self.assertIn("EXTRA_SHIP_DATA: true", said[0])

    def test_a_pending_entry_is_still_not_flushed_on_the_default(self):
        """Belt and braces: the flush has its own gate, for an entry that got in while
        the setting was written down and is flushed after it no longer is."""
        settings_mod._explicit_keys.add("EXTRA_SHIP_DATA")
        with _Settings({"EXTRA_SHIP_DATA": True}):
            self.assertEqual(self.sdm.ship_data_merge_mod(self.MOD, "Probe"), 1)
        settings_mod._explicit_keys.discard("EXTRA_SHIP_DATA")
        with _Settings({}):
            self.assertIsNone(self.sdm.ship_data_flush_mod_file(self.dir))
        self.assertEqual(self.files(), [])

    def test_a_mission_that_WROTE_the_setting_still_gets_its_file(self):
        settings_mod._explicit_keys.add("EXTRA_SHIP_DATA")
        with _Settings({"EXTRA_SHIP_DATA": True}):
            self.assertEqual(self.sdm.ship_data_merge_mod(self.MOD, "Probe"), 1)
            self.assertEqual(self.sdm.ship_data_flush_mod_file(self.dir), self.path)
        self.assertEqual(self.files(), [self.sdm.EXTRA_SHIP_DATA])

    def test_a_mission_with_NO_extra_ship_data_hears_nothing_and_gets_nothing(self):
        """Nothing declared: no warning, no file, nothing replayed, nothing untold."""
        with _Settings({}):
            self.assertIsNone(self.sdm.ship_data_flush_mod_file(self.dir))
            self.assertEqual(self.sd.extra_replay(), 0)
            self.assertEqual(self.sd.extra_report_untold(), [])
        self.assertEqual(self.files(), [])
        self.assertEqual(self.said, [])
