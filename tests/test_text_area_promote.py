"""A one-line `$text:` message that does not FIT must stop being a simple label.

The bug this pins: TextArea decided simple-vs-rich in its `value` setter, where
"one line" can only mean "contains no newline" -- the widget has no bounds yet.
So a whole paragraph passed as `gui_text_area(f"$text:{desc};font:gui-2;")` took
the fast path: ONE send_gui_text across the widget's rect, no wrap accounting,
no scrollbar. The engine wraps it anyway and does not clip, so the tail was
drawn below the widget -- LM's mission picker spilling its description out of
the bottom of the list item.

The fix re-asks the question at present time, where the bounds exist. These
tests therefore drive `_present`, not `calc_rich`: the promotion is a property of
the draw path, and calling calc_rich directly would skip the decision entirely.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.layout.text_area import TextArea, TextLine
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout import measure


class FakeEvent:
    client_id = 0


# A real LM-shaped mission description: prose, one line, no newlines anywhere.
LONG_DESC = (
    "The ambassadors are meeting secretly at starbase Phoenix. Raiders have "
    "learned of the meeting and are moving to intercept. Defend the station "
    "until the delegation has finished and escort the ambassador clear of the "
    "system before the raiders can reach him."
)


class TestTextAreaPromote(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        self.sbs = mock_sbs
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        measure.measure_cache_clear()

    def tearDown(self):
        measure.measure_cache_clear()
        FrameContext.context = None

    def _area(self, message, bounds):
        ta = TextArea("t", message)
        ta.tag = "t"
        ta.bounds = bounds
        ta.client_id = 0
        return ta

    # A listbox item's slice of the LM picker: wide, and only a few lines tall.
    ITEM = Bounds(2.0, 30.0, 45.0, 42.0)

    def test_a_paragraph_that_does_not_fit_is_promoted(self):
        ta = self._area(f"$text:{LONG_DESC};justify: left;color:#999;font:gui-2;",
                        Bounds(self.ITEM))
        self.assertTrue(ta.simple_text, "starts on the fast path, as before")

        ta._present(FakeEvent())

        self.assertFalse(ta.simple_text, "should have promoted to rich")
        self.assertGreater(len(ta.lines), 1, "must be wrapped into display lines")
        self.assertTrue(ta.need_v_scroll,
                        "taller than its bounds -- it needs the scrollbar")

    def test_wrapped_lines_fit_the_widget_they_draw_in(self):
        """The point of promoting: every drawn line is one the widget accounts
        for, at the width it is drawn at. That is what stops the spill."""
        ta = self._area(f"$text:{LONG_DESC};font:gui-2;", Bounds(self.ITEM))
        ta._present(FakeEvent())

        ar = FrameContext.aspect_ratios[0]
        draw_px = int((ta.bounds.width) / 100 * ar.x
                      - (TextArea.V_SCROLL_PX if ta.need_v_scroll else 0))
        for line in ta.lines:
            if not getattr(line, "text", None):
                continue
            with self.subTest(text=line.text[:40]):
                drawn = measure.measure_block_height("gui-2", line.text, draw_px)
                self.assertGreaterEqual(round(line.height + 1e-6, 4),
                                        round(drawn / ar.y * 100, 4))

    def test_text_that_fits_keeps_the_cheap_path(self):
        # The overwhelmingly common case -- a one-line styled label -- must not
        # start paying for the rich parse.
        ta = self._area("$text:Ready;font:gui-2;", Bounds(0.0, 0.0, 90.0, 40.0))
        ta._present(FakeEvent())
        self.assertTrue(ta.simple_text)
        self.assertEqual([], ta.lines)

    def test_promotion_does_not_turn_the_text_into_markdown(self):
        """The author wrote a styled LABEL. A description that happens to open
        with '-' or a digit must not silently become a bullet or a numbered item
        -- which is exactly what the plain rich path would do to it."""
        for lead in ("- ", "3 ", "# "):
            with self.subTest(lead=lead):
                ta = self._area(f"$text:{lead}{LONG_DESC};font:gui-2;",
                                Bounds(self.ITEM))
                ta._present(FakeEvent())
                self.assertFalse(ta.simple_text)
                first = ta.lines[0].text
                self.assertTrue(
                    first.startswith(lead.strip()),
                    f"leading {lead!r} was eaten by markdown: {first[:40]!r}")

    def test_the_messages_own_style_survives_promotion(self):
        # The rich path builds its own message and never appends the cascade,
        # so the props on the original message have to come through.
        ta = self._area(f"$text:{LONG_DESC};justify: left;color:#999;font:gui-2;",
                        Bounds(self.ITEM))
        ta._present(FakeEvent())
        line = next(l for l in ta.lines if isinstance(l, TextLine))
        style = line.style.get("style", "")
        self.assertIn("color:#999", style)
        self.assertIn("font:gui-2", style)

    def test_a_semicolon_in_the_description_is_not_lost(self):
        # Backtick-quoted (what gui_text_escape produces): the ':' and ';' are
        # text, not style props, and must survive the round trip.
        desc = LONG_DESC + " Warning: raiders inbound; hold the line."
        ta = self._area(f"$text:`{desc}`;font:gui-2;", Bounds(self.ITEM))
        ta._present(FakeEvent())
        joined = " ".join(l.text for l in ta.lines if isinstance(l, TextLine))
        self.assertIn("hold the line.", joined)

    def test_promotion_is_stable_across_frames(self):
        # Promotion is one-way until the value is re-set -- re-deciding each
        # frame could oscillate, since the rich form is what makes it fit.
        ta = self._area(f"$text:{LONG_DESC};font:gui-2;", Bounds(self.ITEM))
        ta._present(FakeEvent())
        first = (ta.simple_text, len(ta.lines), ta.need_v_scroll)
        ta._present(FakeEvent())
        ta._present(FakeEvent())
        self.assertEqual(first, (ta.simple_text, len(ta.lines), ta.need_v_scroll))

    def test_a_new_short_value_returns_to_the_cheap_path(self):
        ta = self._area(f"$text:{LONG_DESC};font:gui-2;", Bounds(self.ITEM))
        ta._present(FakeEvent())
        self.assertFalse(ta.simple_text)

        ta.value = "$text:Ready;font:gui-2;"
        ta._present(FakeEvent())
        self.assertTrue(ta.simple_text, "the decision is re-made per value")


if __name__ == "__main__":
    unittest.main()
