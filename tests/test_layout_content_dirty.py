"""The dirty-escalation guard.

Content sizing inherently turns a text change into a LAYOUT change: if a column
is as wide as its text, new text may mean a new width. Done naively that
converts today's cheap "re-send one widget" path into a full subtree re-calc on
every value update -- the single biggest performance risk in the feature.

The guard escalates only when a column is content-sized AND its measured size
actually moved. These tests assert on Dirty's contents directly, because the
thing being tested is WHICH object gets marked, not whether something did.
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.pages.layout import measure


class StubSbs:
    def get_text_line_width(self, font, text):
        return len(text) * 10

    def get_text_line_height(self, font, text):
        return 20

    def get_text_block_height(self, font, text, px_width):
        per_line = max(1, px_width // 10)
        lines, cur = 1, 0
        for word in text.split():
            need = len(word) if cur == 0 else cur + 1 + len(word)
            if need > per_line and cur:
                lines += 1
                cur = len(word)
            else:
                cur = need
        return lines * 20


def _text(label, width=None):
    t = Text("t", f"$text:`{label}`;font:gui-2;")
    if width is not None:
        t.set_col_width(StyleDefinition.parse(f"col-width: {width};")["col-width"])
    return t


class _Base(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=StubSbs(), sim=None, event=types.SimpleNamespace(client_id=0))
        measure.measure_cache_clear()
        Dirty.dirty = {}

    def tearDown(self):
        FrameContext.context = None
        Dirty.dirty = {}
        measure.measure_cache_clear()

    def build(self, cols):
        row = Row()
        for c in cols:
            row.add(c)
        sec = Layout("sec", [row], 0, 0, 100, 100)
        sec.calc(0)
        # calc() assigns parents/client ids; presenting is not needed, but the
        # widgets must have a client_id for Dirty to accept them.
        for c in row.columns:
            c.client_id = 0
        sec.client_id = 0
        Dirty.dirty = {}
        return sec, row

    def marked(self):
        return [o for s in Dirty.dirty.values() for o in s]


class TestNonContentStaysCheap(_Base):
    """The common case: a layout with no content keywords must behave exactly
    as it did before this feature existed."""

    def test_plain_text_update_marks_only_the_widget(self):
        t = _text("HELLO")
        sec, row = self.build([t, _text("other")])
        t.update("$text:`GOODBYE`;font:gui-2;")
        self.assertIn(t, self.marked())
        self.assertNotIn(sec, self.marked())

    def test_plain_widget_is_never_content_sized(self):
        t = _text("HELLO")
        self.build([t, _text("other")])
        self.assertFalse(t.content_sized)


class TestContentSizedEscalatesOnlyWhenSizeMoves(_Base):
    def test_same_width_text_stays_visual_only(self):
        # Same length -> same measured width -> no re-layout needed.
        t = _text("HELLO", "content")
        sec, row = self.build([t, _text("flex")])
        self.assertTrue(t.content_sized)
        t.update("$text:`WORLD`;font:gui-2;")     # also 5 chars
        self.assertIn(t, self.marked())
        self.assertNotIn(sec, self.marked(),
                         "same-size text should not force a re-layout")

    def test_different_width_text_marks_the_layout(self):
        t = _text("HELLO", "content")
        sec, row = self.build([t, _text("flex")])
        t.update("$text:`A MUCH LONGER LABEL`;font:gui-2;")
        self.assertIn(sec, self.marked(),
                      "content column changed width but no re-layout was queued")

    def test_shrinking_also_marks_the_layout(self):
        t = _text("A MUCH LONGER LABEL", "content")
        sec, row = self.build([t, _text("flex")])
        t.update("$text:`HI`;font:gui-2;")
        self.assertIn(sec, self.marked())


class TestGuardIsConservative(_Base):
    """When the answer is unknown, rebuild rather than render something stale."""

    def test_never_measured_escalates(self):
        t = _text("HELLO", "content")
        t.content_sized = True          # flagged, but no recorded measurement
        t.client_id = 0
        self.assertTrue(t.measured_size_changed())

    def test_unmeasurable_now_escalates(self):
        t = _text("HELLO", "content")
        sec, row = self.build([t, _text("flex")])
        # Metrics genuinely unavailable: no frame context AND a cold memo.
        # (With a warm memo the measurement still succeeds without a context,
        # which is the cache doing its job -- not an escalation case.)
        FrameContext.context = None
        measure.measure_cache_clear()
        self.assertTrue(t.measured_size_changed())

    def test_warm_memo_survives_a_missing_context(self):
        # Documents the behaviour the test above had to work around.
        t = _text("HELLO", "content")
        self.build([t, _text("flex")])
        FrameContext.context = None
        self.assertFalse(t.measured_size_changed())


class TestGuardCostIsCached(_Base):
    """The re-measure the guard costs must be memoized -- it has to be cheaper
    than the calc() it avoids, or the guard is worse than the disease."""

    def test_repeated_same_value_updates_do_not_hit_the_engine(self):
        t = _text("HELLO", "content")
        self.build([t, _text("flex")])
        before = measure.measure_cache_stats()["engine_calls"]
        for _ in range(10):
            t.update("$text:`HELLO`;font:gui-2;")
        after = measure.measure_cache_stats()["engine_calls"]
        self.assertEqual(before, after,
                         "guard re-measured from the engine instead of the memo")


if __name__ == "__main__":
    unittest.main()
