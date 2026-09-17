"""The hail echo: a durable line saying the conversation happened.

A hail is transient. The strip entry disappears on close, the portrait goes, and the only
trace is a history tab nobody opens - so a crew told something important four minutes ago
have no way back to it, and a crew who never picked up never learn they missed anything.

The echo files ONE line in the ship's log. It must never interrupt: the whole point is
that it is there when you go looking, not that it grabs the screen.

    python -m unittest tests.test_hail_echo
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural import hail as H
from sbs_utils.procedural.hail import (
    hail_echo_enable, hail_echo_reset, hail_echo_settings, hail_echo_text,
    hail_offer, hail_accept, hail_close, hail_log)
from sbs_utils.procedural import log_panel as LP
from sbs_utils.procedural.gui import log_panel_gui as LPG
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id


#: A MAST-driven hail (no AMD behind it) - the simplest thing that closes.
def _offer(ship):
    return H.hail_offer(ship, speaker="ds1", name="DS 1",
                        title="Ambassador Kidnapped",
                        lines="We have a problem.",
                        choices=["Take the case"])


class EchoTextTests(unittest.TestCase):
    def test_answered_names_the_choice(self):
        t = hail_echo_text({"name": "DS 1", "title": "Ambassador Kidnapped",
                            "taken": [{"label": "Take the case"}]})
        self.assertEqual(t, "DS 1 - Ambassador Kidnapped - answered (Take the case)")

    def test_answered_without_a_choice_still_reads(self):
        t = hail_echo_text({"name": "DS 1", "title": "X"})
        self.assertEqual(t, "DS 1 - X - answered")

    def test_declined_says_so(self):
        t = hail_echo_text({"name": "DS 1", "title": "X"}, declined=True)
        self.assertEqual(t, "DS 1 - X - not answered")

    def test_it_reuses_the_strips_wording(self):
        """One summarizer, so the log line and the hail row cannot drift apart."""
        rec = {"name": "DS 1", "title": "Ambassador Kidnapped"}
        self.assertTrue(hail_echo_text(rec).startswith(H.hail_answer_label(rec)))

    def test_no_colon_or_semicolon_survives_a_choice_label(self):
        """A row label is a style-property string to the engine, so `:` and `;` in it
        are parsed rather than drawn - and a choice label is authored text."""
        t = hail_echo_text({"name": "A", "title": "B",
                            "taken": [{"label": "Yes: do it; now"}]})
        self.assertNotIn(":", t.split(" - ", 1)[1])
        self.assertNotIn(";", t)

    def test_it_is_ascii(self):
        hail_echo_text({"name": "DS 1", "title": "X",
                        "taken": [{"label": "Take the case"}]}).encode("ascii")


class EchoBehaviorTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        hail_echo_reset()
        LP.log_clear()
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def tearDown(self):
        hail_echo_reset()

    def _entries(self):
        return LP.log_entries(self.ship) or []

    def _run_hail(self, answer=True):
        _offer(self.ship)
        hail_accept(self.ship)
        if answer:
            H.hail_answer(self.ship, 0)
        else:
            hail_close(self.ship, declined=True)

    # --- the back-compat guarantee -------------------------------------------
    def test_off_by_default(self):
        """Turning this on for every shipped mission is a change nobody asked for."""
        self.assertEqual(hail_echo_settings(), (False, True))

    def test_off_means_not_one_line(self):
        self._run_hail()
        self.assertEqual(self._entries(), [])

    # --- on -------------------------------------------------------------------
    def test_on_files_exactly_one_line(self):
        hail_echo_enable(True)
        self._run_hail()
        self.assertEqual(len(self._entries()), 1)

    def test_the_line_records_the_answer(self):
        hail_echo_enable(True)
        self._run_hail()
        self.assertIn("Take the case", str(self._entries()[0]))

    def test_an_unanswered_hail_echoes_too(self):
        """The MORE important case: an answered hail at least left a conversation
        behind, while one nobody picked up otherwise vanishes without trace."""
        hail_echo_enable(True)
        self._run_hail(answer=False)
        self.assertEqual(len(self._entries()), 1)
        self.assertIn("not answered", str(self._entries()[0]))

    def test_declined_can_be_turned_off_on_its_own(self):
        hail_echo_enable(True, declined=False)
        self._run_hail(answer=False)
        self.assertEqual(self._entries(), [])

    def test_it_does_not_replace_the_archive(self):
        """The echo points at the conversation; hail_log still holds it."""
        hail_echo_enable(True)
        self._run_hail()
        self.assertEqual(len(hail_log(self.ship)), 1)

    # --- THE RULE -------------------------------------------------------------
    def test_it_never_raises_a_panel(self):
        """Nothing new may interrupt. log_notify's raise is gated on RAISE_ON, which is
        empty - this asserts the gate rather than trusting it, because a later mission
        setting RAISE_ON would otherwise silently turn every hail close into a panel
        grab on every console of the ship."""
        hail_echo_enable(True)
        calls = []
        real = LPG.log_raise
        LPG.log_raise = lambda *a, **kw: calls.append(a)
        try:
            self._run_hail()
            self._run_hail(answer=False)
        finally:
            LPG.log_raise = real
        self.assertEqual(calls, [])

    def test_a_broken_log_does_not_cost_the_hail_its_close(self):
        real = LPG.log_notify
        LPG.log_notify = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("x"))
        try:
            hail_echo_enable(True)
            _offer(self.ship)
            hail_accept(self.ship)
            self.assertTrue(hail_close(self.ship))
        finally:
            LPG.log_notify = real

    # --- reset ----------------------------------------------------------------
    def test_a_mission_reset_puts_the_dial_back(self):
        """A mission that opted in must not opt the NEXT one in."""
        hail_echo_enable(True)
        H.hail_reset()
        self.assertEqual(hail_echo_settings(), (False, True))


if __name__ == "__main__":
    unittest.main()
