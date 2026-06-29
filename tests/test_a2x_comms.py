"""Tests for a2x scripted-message helpers."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.a2x.comms import (
    _clean, console_roles, incoming_comms_text, big_message, warning_popup,
    spawn_external_program,
)
from sbs_utils.procedural.spawn import player_spawn


class A2xCommsPureTests(unittest.TestCase):
    def test_clean_converts_caret_newlines(self):
        self.assertEqual(_clean("a^b^^c"), "a\nb\n\nc")

    def test_clean_handles_none_and_whitespace(self):
        self.assertEqual(_clean(None), "")
        self.assertEqual(_clean("  hi  "), "hi")

    def test_spawn_external_program_missing_is_safe(self):
        # an absolute, non-existent program -> None (logged), never raises
        self.assertIsNone(spawn_external_program("/no/such/player.exe", "--play x.mp4"))

    def test_console_roles_maps_letters(self):
        self.assertEqual(console_roles("HW"), "helm,weapons")
        self.assertEqual(console_roles("MHWESCO"),
                         "mainscreen,helm,weapons,engineering,science,comms,operations")
        self.assertEqual(console_roles("xZ"), "")  # unknown letters dropped
        self.assertEqual(console_roles(None), "")


class A2xCommsMockTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        # a player ship so role("__player__") resolves to a real target
        player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser")

    def test_incoming_comms_text_no_crash(self):
        # Should broadcast to players without raising.
        incoming_comms_text("Hello, Captain.^Proceed to DS38.", from_name="Admiral")

    def test_big_message_no_crash(self):
        big_message("THE END OF PEACE", "written by Thom Robertson")

    def test_warning_popup_no_crash(self):
        warning_popup("Shields failing!^Reroute power.", consoles="HE")


if __name__ == "__main__":
    unittest.main()
