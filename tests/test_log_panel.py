"""Log Panel store + renderer (LOG_PANEL_PLAN.md).

The data half of the text waterfall's replacement. It is deliberately GUI-free so the
part that decides what a player reads is testable at all - the waterfall never was.

    python -m unittest tests.test_log_panel
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import log_panel as LP


class StoreTests(unittest.TestCase):
    def setUp(self):
        LP.log_clear()

    def test_untagged_lands_in_log_and_nowhere_else(self):
        """The migration promise: nothing is lost by not being tagged."""
        LP.log_add(1, "plain message")
        self.assertEqual(1, len(LP.log_entries(1, LP.TAB_LOG)))
        self.assertEqual(0, len(LP.log_entries(1, LP.TAB_SHIP)))
        self.assertEqual(0, len(LP.log_entries(1, LP.TAB_MISSION)))

    def test_log_tab_shows_everything(self):
        LP.log_add(1, "plain")
        LP.log_add(1, "hull breach", category=LP.TAB_SHIP)
        LP.log_add(1, "objective done", category=LP.TAB_MISSION)
        self.assertEqual(3, len(LP.log_entries(1, LP.TAB_LOG)))
        self.assertEqual(1, len(LP.log_entries(1, LP.TAB_SHIP)))

    def test_scopes_do_not_bleed(self):
        """Ship-scoped: one crew's log is not another's."""
        LP.log_add(1, "ours")
        LP.log_add(2, "theirs")
        self.assertEqual(["ours"], [e["text"] for e in LP.log_entries(1)])

    def test_the_ring_caps_and_keeps_the_NEWEST(self):
        for i in range(LP.LOG_CAP + 50):
            LP.log_add(1, f"line {i}")
        got = LP.log_entries(1)
        self.assertEqual(LP.LOG_CAP, len(got))
        self.assertEqual(f"line {LP.LOG_CAP + 49}", got[-1]["text"])

    def test_seq_is_monotonic_across_the_wrap(self):
        """`seq` is not an index. A reader scrolled back needs a stable count while the
        ring drops entries off the top underneath them."""
        for i in range(LP.LOG_CAP + 10):
            LP.log_add(1, f"line {i}")
        seqs = [e["seq"] for e in LP.log_entries(1)]
        self.assertEqual(sorted(seqs), seqs, "seq must stay ordered")
        self.assertEqual(len(set(seqs)), len(seqs), "seq must stay unique")
        self.assertGreater(seqs[0], 1, "the earliest surviving entry is not the first ever")

    def test_clear_empties_every_scope(self):
        LP.log_add(1, "a")
        LP.log_add(2, "b")
        LP.log_clear()
        self.assertEqual(0, LP.log_size())


class RenderTests(unittest.TestCase):
    def setUp(self):
        LP.log_clear()

    def _render(self, scope=1, tab=LP.TAB_LOG):
        return LP.log_render(LP.log_entries(scope, tab))

    def test_one_entry_is_one_line(self):
        """A style slot maps to an entry by index, so this has to hold."""
        for i in range(4):
            LP.log_add(1, f"line {i}")
        text, styles = self._render()
        self.assertEqual(4, len(text.splitlines()))
        self.assertEqual(4, len(styles))

    def test_embedded_newlines_are_flattened(self):
        """A log line that silently became three would break the index mapping."""
        LP.log_add(1, "first\nsecond^third")
        text, styles = self._render()
        self.assertEqual(1, len(text.splitlines()))
        self.assertEqual(1, len(styles))

    def test_a_plain_entry_carries_no_box(self):
        """Day-one parity: an untagged line must look like a waterfall line.

        It DOES carry a font - log text runs a size down from document text - so the
        assertion is about colour and boxing, not about the slot being empty."""
        LP.log_add(1, "just text")
        text, styles = self._render()
        self.assertEqual("just text", text)
        self.assertNotIn("color:", styles[0]["style"], "a plain line must not be coloured")
        self.assertIsNone(styles[0].get("background"), "a plain line must not be boxed")

    def test_severity_becomes_a_callout(self):
        LP.log_add(1, "Hull breach", severity="danger")
        text, styles = self._render()
        self.assertNotIn("[!", text, "callout markup must be consumed, not shown")
        self.assertIn("Hull breach", text)
        self.assertIsNotNone(styles[0])
        self.assertTrue(styles[0].get("background"), "a severity entry should draw a box")

    def test_category_colors_without_boxing(self):
        LP.log_add(1, "Docked at DS 1", category=LP.TAB_SHIP)
        text, styles = self._render()
        self.assertEqual("Docked at DS 1", text)
        self.assertIn("color:", styles[0]["style"])
        self.assertIsNone(styles[0].get("background"),
                          "a category must not cost a box - that is severity's job")

    def test_an_explicit_color_beats_the_category(self):
        LP.log_add(1, "urgent-ish", color="#f00", category=LP.TAB_SHIP)
        _text, styles = self._render()
        self.assertIn("#f00", styles[0]["style"])

    def test_mixed_entries_keep_their_index_alignment(self):
        LP.log_add(1, "plain one")
        LP.log_add(1, "Shields critical", severity="warning")
        LP.log_add(1, "Docked", category=LP.TAB_SHIP)
        text, styles = self._render()
        lines = text.splitlines()
        self.assertEqual(3, len(lines))
        self.assertEqual(3, len(styles))
        self.assertNotIn("color:", styles[0]["style"])     # plain: font only
        self.assertTrue(styles[1].get("background"))       # callout: boxed
        self.assertIn("color:", styles[2]["style"])        # category: coloured...
        self.assertIsNone(styles[2].get("background"))     # ...but not boxed

    def test_empty_renders_without_raising(self):
        text, styles = self._render()
        self.assertEqual("", text)
        self.assertFalse(styles)

    def test_render_is_pure(self):
        """No globals, no GUI - the same entries render the same twice."""
        LP.log_add(1, "a", category=LP.TAB_SHIP)
        LP.log_add(1, "b", severity="tip")
        entries = LP.log_entries(1)
        self.assertEqual(LP.log_render(entries), LP.log_render(entries))
