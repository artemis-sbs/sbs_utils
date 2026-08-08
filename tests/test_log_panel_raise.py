"""Urgent log entries raise the log tab; routine ones must not (LOG_PANEL_PLAN.md step 5).

The plan's "collapse until the next content" became "raise on the content that matters",
because the log mounted as info-panel TABS rather than a standalone panel - see the plan.
The rule is the same one the plan settled: routine traffic is silent, warning/danger
interrupts, and a completion does NOT (good news can wait).

    python -m unittest tests.test_log_panel_raise
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.comms import comms_broadcast
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural import log_panel as LP
from sbs_utils.procedural.gui import log_panel_gui as LPG


class RaiseTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        LP.log_clear()
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))
        self.raised = []
        self._real = LPG.log_raise
        LPG.log_raise = lambda scope, tab=LP.TAB_LOG: self.raised.append((scope, tab))

    def tearDown(self):
        LPG.log_raise = self._real

    def test_routine_traffic_does_not_interrupt(self):
        comms_broadcast(self.ship, "chatter")
        comms_broadcast(self.ship, "docked at DS 1", category="ship")
        self.assertEqual([], self.raised,
                         "routine traffic must never grab the console")

    def test_a_completion_does_not_interrupt(self):
        """`tip` is good news - it can wait for the player to look."""
        comms_broadcast(self.ship, "Quest complete: Rock Breakers",
                        category="mission", severity="tip")
        self.assertEqual([], self.raised)

    def test_a_warning_raises(self):
        comms_broadcast(self.ship, "Shields critical", category="ship", severity="warning")
        self.assertEqual(1, len(self.raised))

    def test_danger_raises(self):
        comms_broadcast(self.ship, "Hull breach", category="ship", severity="danger")
        self.assertEqual(1, len(self.raised))

    def test_the_entry_is_still_logged_when_it_raises(self):
        """Raising is in addition to recording, never instead of it."""
        comms_broadcast(self.ship, "Hull breach", category="ship", severity="danger")
        self.assertEqual(1, len(LP.log_entries(self.ship, LP.TAB_SHIP)))

    def test_a_raise_failure_cannot_break_a_broadcast(self):
        """The waterfall is still what ships; the replacement must not take it down."""
        LPG.log_raise = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        comms_broadcast(self.ship, "Hull breach", category="ship", severity="danger")
        # No exception, and the message still reached the log.
        self.assertEqual(1, len(LP.log_entries(self.ship)))
