"""A TextArea must MEASURE at the width it will DRAW at.

The bug this pins: calc_rich measured wrapping against the full bounds width
while the draw path subtracted the scrollbar's 20px. When a scrollbar was
present the engine wrapped a line nobody had counted, and because the engine
does not clip, that line was drawn ON TOP of its neighbour.

It was visible for a long time in LM's Library document at 1024x768 -- long
enough to always scroll -- as paragraphs bleeding into each other. Only some
paragraphs showed it, which is what made it look random: it needs a wrap point
to fall inside that 20px band.

These tests work on the WIDTHS rather than on rendered output, because that is
where the bug lives -- a measurement taken against a width that is never used.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.layout.text_area import TextArea
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout import measure


class FakeEvent:
    client_id = 0


# The real paragraph from the LM Library document that overlapped on screen.
ARVONIAN = (
    "If you've ever met a snob who literally believes his feces doesn't stink, "
    "he was probably an Arvonian. Also, he may have been a she. Adult Arvonians "
    "are the size and shape of pre-pubescent humans, so we outsiders struggle "
    "to tell Arvonian males and females apart. This has given the galaxy many "
    "hilarious jokes about bars and the people who walk into them."
)

# Long enough that the area always scrolls.
LONG_DOC = "\n\n".join([ARVONIAN] * 12)


class TestTextAreaScrollWidth(unittest.TestCase):
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

    def _area(self, text, bounds):
        ta = TextArea("t", f"$text:`{text}`;font:gui-2;")
        ta.tag = "t"
        ta.bounds = bounds
        ta.client_id = 0
        return ta

    def _draw_px(self, ta, with_scroll):
        ar = FrameContext.aspect_ratios[0]
        px = (ta.bounds.right - ta.bounds.left) / 100 * ar.x
        if with_scroll:
            px -= TextArea.V_SCROLL_PX
        return int(px)

    def test_every_line_is_allocated_the_height_it_will_draw(self):
        """The regression itself.

        TextArea pre-wraps into display lines and sends each as its own
        send_gui_text. Every line's allocated height must cover what the ENGINE
        draws for that line AT THE WIDTH IT IS DRAWN AT.
        """
        ta = self._area(LONG_DOC, Bounds(35.0, 5.0, 99.0, 60.0))
        ta.calc_rich(0)
        self.assertTrue(ta.need_v_scroll,
                        "test needs a scrolling area to be meaningful")

        ar = FrameContext.aspect_ratios[0]
        draw_px = self._draw_px(ta, with_scroll=True)
        for line in ta.lines:
            if not line.text:
                continue
            with self.subTest(text=line.text[:40]):
                drawn = measure.measure_block_height("gui-2", line.text, draw_px)
                self.assertGreaterEqual(
                    round(line.height + 1e-6, 4),
                    round(drawn / ar.y * 100, 4),
                    "line measured wider than it draws -- it will overlap")

    def test_non_scrolling_area_keeps_the_full_width(self):
        # The fix must not cost 20px in the common case of no scrollbar.
        ta = self._area(ARVONIAN, Bounds(0.0, 0.0, 100.0, 90.0))
        ta.calc_rich(0)
        self.assertFalse(ta.need_v_scroll)
        self.assertEqual(self._draw_px(ta, with_scroll=False),
                         int((ta.bounds.right - ta.bounds.left) / 100
                             * FrameContext.aspect_ratios[0].x))

    def test_the_scrollbar_decision_is_stable(self):
        """The re-run must settle, not oscillate.

        Reserving the scrollbar makes the text taller, which can only keep the
        scrollbar -- but calc twice and require the same answer, so a future
        change cannot introduce a flip-flop unnoticed.
        """
        ta = self._area(LONG_DOC, Bounds(35.0, 5.0, 99.0, 60.0))
        ta.calc_rich(0)
        first = (ta.need_v_scroll, len(ta.lines))
        ta.calc_rich(0)
        self.assertEqual(first, (ta.need_v_scroll, len(ta.lines)))


if __name__ == "__main__":
    unittest.main()
