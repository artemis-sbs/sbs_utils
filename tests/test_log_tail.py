"""The ambient log tail: newest FIRST, and only the last few (LOG_PANEL_PLAN.md).

Newest-first is not just simpler. The newest line stays in the SAME PLACE, so an ambient
strip is read at a glance instead of tracking a line that moves - and it takes the strip
off the scroll machinery, which is what kept the engine showing the top of it.
`gui_panel_console_message_list` already reads newest-first for the same reason.

    python -m unittest tests.test_log_tail
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import log_panel as LP


def tail(scope, count=None, tab=LP.TAB_LOG):
    """What gui_log_tail feeds the widget - the selection and ORDER, without the GUI."""
    entries = LP.log_entries_union([scope], tab)
    count = LP.LOG_TAIL_LINES if count is None else count
    if count > 0:
        entries = entries[-count:]
    return [e["text"] for e in reversed(entries)]


class TailTests(unittest.TestCase):
    def setUp(self):
        LP.log_clear()
        for n in ("first", "second", "third", "fourth"):
            LP.log_add(1, n)

    def test_newest_is_first(self):
        self.assertEqual("fourth", tail(1)[0])

    def test_only_the_last_few(self):
        self.assertEqual(LP.LOG_TAIL_LINES, len(tail(1)))

    def test_the_default_is_two(self):
        """One is a headline; three starts competing with the panel holding the history."""
        self.assertEqual(2, LP.LOG_TAIL_LINES)

    def test_order_within_the_tail_is_newest_down(self):
        self.assertEqual(["fourth", "third"], tail(1))

    def test_a_shorter_log_than_the_tail_is_fine(self):
        LP.log_clear()
        LP.log_add(1, "only one")
        self.assertEqual(["only one"], tail(1))

    def test_an_empty_log_is_fine(self):
        LP.log_clear()
        self.assertEqual([], tail(1))

    def test_a_tail_can_follow_one_tab(self):
        LP.log_clear()
        LP.log_add(1, "chatter")
        LP.log_add(1, "hull breach", category=LP.TAB_SHIP)
        self.assertEqual(["hull breach"], tail(1, count=2, tab=LP.TAB_SHIP))
