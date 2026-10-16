"""A text area breaks where the ENGINE's wrap breaks - never a sentence cut mid-way.

Engine-seen, author course 3 lesson 13 (the xESS Tasks page, Lt Dana Ross, Find a Place
to Set Down). The quest's one-line description drew as

    If the beacon cannot be lit, somebody
    will
    have to fly a new one down.

The text area broke the paragraph into lines with the engine's LINE-WIDTH metric, and
`If the beacon cannot be lit, somebody will` measured as fitting. The engine's own wrap -
the one that draws, and the one `get_text_block_height` reports - broke it once more, so
the row was sized for two lines and `will` sat alone on the second. The objective above it
did the same (`... could` / `land`). Two engine metrics that disagree at the margin; the
wrap is the one that is drawn, so it decides.

The mock's two metrics agree, so this test gives it an engine-like wrap that is a few
pixels narrower than the line metric.

    python -m unittest tests.test_text_area_engine_wrap
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
import unittest

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.pages.layout import measure as M
from sbs_utils.pages.layout.text_area import TextArea
from sbs_utils.pages.layout.bounds import Bounds

CID = 0x8000000000000091
SENTENCE = "If the beacon cannot be lit, somebody will have to fly a new one down."
#: How much narrower the engine's wrap is than its line-width metric, in this test.
INSET_PX = 12


class TheEnginesWrapDecides(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(CID))
        self.addCleanup(setattr, FrameContext, "context", None)
        FrameContext.aspect_ratios[CID] = Vec3(1280, 960, 0)
        self.addCleanup(FrameContext.aspect_ratios.pop, CID, None)
        orig = mock_sbs.get_text_block_height

        def engine_like(font, text, width):
            return orig(font, text, max(1, int(width) - INSET_PX))

        mock_sbs.get_text_block_height = engine_like
        self.addCleanup(setattr, mock_sbs, "get_text_block_height", orig)
        M.measure_cache_clear()
        self.addCleanup(M.measure_cache_clear)

    def width_where_only_the_wrap_breaks(self):
        """A width at which the line metric says the first N words fit and the wrap does
        not - the margin the engine shot fell into."""
        words = SENTENCE.split()
        for n in range(3, len(words)):
            head = " ".join(words[:n])
            w = M.measure_line_width("gui-2", head)
            if w < 300:
                continue            # a realistic column, as the xESS's ~400px pane
            if M.measure_block_height("gui-2", head, w) > M.measure_line_height("gui-2", head):
                return w
        self.fail("fixture: no width where the two metrics disagree")

    def lines_of(self, px):
        ta = TextArea("ta_wrap", "")
        pct = px / 1280.0 * 100.0
        ta.bounds = Bounds(10, 10, 10 + pct, 90)
        # Two paragraphs, as the Tasks page has (its objective, then the description):
        # a single plain line takes the text area's fast path and is never broken here.
        ta.value = "Objective\n\n" + SENTENCE
        ta.calc_rich(CID)
        lines = [ln.text for ln in ta.lines if getattr(ln, "text", None)]
        self.assertEqual("Objective", lines[0], "fixture: %r" % lines)
        return lines[1:]

    def test_every_line_is_ONE_line_by_the_engines_wrap(self):
        px = self.width_where_only_the_wrap_breaks()
        lines = self.lines_of(px)
        self.assertEqual(SENTENCE, " ".join(lines), "a word was lost")
        for line in lines:
            self.assertLessEqual(
                M.measure_block_height("gui-2", line, px),
                M.measure_line_height("gui-2", line),
                "the engine wraps %r again at %dpx - an orphan word on screen" % (line, px))

    def test_wrap_to_width_says_the_same(self):
        px = self.width_where_only_the_wrap_breaks()
        for line in M.wrap_to_width("gui-2", SENTENCE, px):
            self.assertLessEqual(M.measure_block_height("gui-2", line, px),
                                 M.measure_line_height("gui-2", line), line)


if __name__ == "__main__":
    unittest.main()
