"""gui_add_console_type duplicate-registration tests.

Regression: re-registering a console path (e.g. an in-process recompile on
run_next_mission, where the __CONSOLE_TYPES__ registry already holds the previous
compile's paths) used to raise "'dict' object has no attribute 'label'" - the
duplicate-handling branch did attribute access on the plain dict instead of reading
the label object under the "label" key.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.procedural.gui.console_types import gui_add_console_type, gui_get_console_types


class _FakeLabel:
    def __init__(self, priority, desc="", weight=101):
        self.priority = priority
        self.desc = desc
        self.raw_weight = weight

    def test(self, task):
        return True


class TestConsoleTypes(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()
        Agent.SHARED.set_inventory_value("__CONSOLE_TYPES__", {})

    def test_duplicate_path_does_not_crash(self):
        # The recompile case: same path registered twice must not raise.
        gui_add_console_type("helm", "Helm", None, _FakeLabel(100))
        gui_add_console_type("helm", "Helm", None, _FakeLabel(100))   # duplicate
        self.assertIn("helm", gui_get_console_types())

    def test_higher_priority_existing_is_kept(self):
        keep = _FakeLabel(200)
        gui_add_console_type("eng", "Eng", None, keep)
        gui_add_console_type("eng", "Eng2", None, _FakeLabel(100))    # lower -> ignored
        self.assertIs(gui_get_console_types()["eng"]["label"], keep)

    def test_higher_priority_new_overwrites(self):
        gui_add_console_type("wep", "Wep", None, _FakeLabel(100))
        new = _FakeLabel(150)
        gui_add_console_type("wep", "Wep2", None, new)                # higher -> wins
        self.assertIs(gui_get_console_types()["wep"]["label"], new)


if __name__ == "__main__":
    unittest.main()
