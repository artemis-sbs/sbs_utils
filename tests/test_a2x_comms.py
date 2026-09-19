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


class A2xCommsButtonTests(unittest.TestCase):
    """2.8 comms buttons exist only between set_comms_button and clear_comms_button."""

    def setUp(self):
        self.sim = reset_mock(sbs)
        from sbs_utils.procedural.a2x.sides import declare_sides
        from sbs_utils.procedural.query import to_id
        declare_sides([1, 2])
        self.friendly = to_id(player_spawn(0, 0, 0, "Artemis", "friendly", "tsn_light_cruiser"))
        self.enemy = to_id(player_spawn(0, 0, 0, "Raider", "enemy", "tsn_light_cruiser"))

    def test_a_button_is_hidden_until_set(self):
        from sbs_utils.procedural.a2x.comms import set_comms_button, comms_button_visible
        self.assertFalse(comms_button_visible("MAYDAY", self.friendly))
        set_comms_button("MAYDAY")
        self.assertTrue(comms_button_visible("MAYDAY", self.friendly))

    def test_clear_withdraws_it_again(self):
        from sbs_utils.procedural.a2x.comms import (set_comms_button, clear_comms_button,
                                                    comms_button_visible)
        set_comms_button("MAYDAY", 0)
        clear_comms_button("MAYDAY")
        self.assertFalse(comms_button_visible("MAYDAY", self.friendly))
        clear_comms_button("MAYDAY")          # clearing a missing button is harmless

    def test_side_scoped_button_shows_only_on_that_side(self):
        from sbs_utils.procedural.a2x.comms import (set_comms_button, clear_comms_button,
                                                    comms_button_visible)
        set_comms_button("Bounty", 2)
        self.assertTrue(comms_button_visible("Bounty", self.friendly))
        self.assertFalse(comms_button_visible("Bounty", self.enemy))
        set_comms_button("Bounty", 1)
        clear_comms_button("Bounty", 2)
        self.assertFalse(comms_button_visible("Bounty", self.friendly))
        self.assertTrue(comms_button_visible("Bounty", self.enemy))


class CommsRefreshOpenTests(unittest.TestCase):
    """comms_refresh_open re-runs every open comms menu, and comms_navigate_override no
    longer gives up at the first pair with no menu open."""

    class _Prom:
        def __init__(self, path):
            self.path = path
            self.calls = []

        def set_path(self, path):
            self.calls.append(path)

    class _Task:
        def __init__(self, prom):
            self.prom = prom

        def get_variable(self, name):
            return self.prom if name == "BUTTON_PROMISE" else None

    def setUp(self):
        import sbs_utils.procedural.comms as C
        self.reg = getattr(C, "__comms_promises")
        self.saved = dict(self.reg)
        self.reg.clear()
        self.a, self.b = self._Prom("comms"), self._Prom("comms/trade")
        self.reg[(11, 21)] = self._Task(self.a)
        self.reg[(12, 22)] = self._Task(self.b)

    def tearDown(self):
        self.reg.clear()
        self.reg.update(self.saved)

    def test_refresh_reruns_each_menu_on_its_own_path(self):
        from sbs_utils.procedural.comms import comms_refresh_open
        self.assertEqual(2, comms_refresh_open())
        self.assertEqual(["//comms"], self.a.calls)
        self.assertEqual(["//comms/trade"], self.b.calls)

    def test_override_skips_a_pair_with_no_menu_instead_of_stopping(self):
        from sbs_utils.procedural import comms as C
        C._comms_override_pair(99, 99, None, True)      # no menu: skipped
        C._comms_override_pair(12, 22, None, True)
        self.assertEqual(["//comms/trade"], self.b.calls)


if __name__ == "__main__":
    unittest.main()
