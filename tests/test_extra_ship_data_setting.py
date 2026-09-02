"""Extra ship data is off unless the mission asks, and the ask is a SETTING.

It was a hardcoded constant from the 2026-08-27 hot fix until 2026-09-01. The reason
it could not stay one: the right answer depends on the INSTALL, not on the build of
the library. The engine only grew a working extra-ship-data path in v1.3.7, and people
are still running v1.3.4 - where a declared hull never registers, and asking to spawn
one dies inside the engine as `bad allocation`, minutes later, against unrelated code.

So off is the default, and a mission that knows which engine it runs on turns it on
with `EXTRA_SHIP_DATA: true` in settings.yaml, a profile, or COSMOS_SETTINGS.
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

    def test_a_mission_that_says_nothing_gets_it_OFF(self):
        """The property that protects every v1.3.4 install."""
        with _Settings({}):
            self.assertFalse(extra_ship_data_enabled())

    def test_setting_it_false_keeps_it_off(self):
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
