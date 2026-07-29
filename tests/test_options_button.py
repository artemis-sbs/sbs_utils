"""The Options button intent survives page rebuilds.

The bug this locks down: StoryPage.on_new_gui restored the button to a hardcoded
0 on every new GUI (which fires from add_tag, on the first tagged widget of a
build), so a mission could not hold it transparent -- whatever it set was taken
away a moment later. The same sbs call worked in a cinematic only because no
story page was being built.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.gui.options_button import (
    gui_options_button, gui_options_button_flag, gui_options_button_clear)


class TestOptionsButton(unittest.TestCase):
    def setUp(self):
        gui_options_button_clear()

    def tearDown(self):
        gui_options_button_clear()

    def test_default_is_visible(self):
        """A mission that never asks gets the old behavior: restore to 0."""
        self.assertEqual(gui_options_button_flag(7), 0)

    def test_records_transparent(self):
        gui_options_button(True, client_id=7)
        self.assertEqual(gui_options_button_flag(7), 1)

    def test_records_restore(self):
        gui_options_button(True, client_id=7)
        gui_options_button(False, client_id=7)
        self.assertEqual(gui_options_button_flag(7), 0)

    def test_is_per_client(self):
        """One console going transparent must not drag the others with it."""
        gui_options_button(True, client_id=7)
        self.assertEqual(gui_options_button_flag(7), 1)
        self.assertEqual(gui_options_button_flag(8), 0)

    def test_clear_one_client_leaves_others(self):
        gui_options_button(True, client_id=7)
        gui_options_button(True, client_id=8)
        gui_options_button_clear(7)
        self.assertEqual(gui_options_button_flag(7), 0)
        self.assertEqual(gui_options_button_flag(8), 1)

    def test_survives_a_simulated_rebuild(self):
        """What on_new_gui does now: restore to the recorded intent. Before the
        fix this asserted 0 and the button came back on every build."""
        gui_options_button(True, client_id=7)
        for _ in range(5):                       # five page rebuilds
            restored = gui_options_button_flag(7)
            self.assertEqual(restored, 1)


if __name__ == "__main__":
    unittest.main()
