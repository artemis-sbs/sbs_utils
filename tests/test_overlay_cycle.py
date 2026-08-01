"""Text that does not fit a one-line slot is played in timed parts, not clipped.

A banner strip and a lower third have a hard width. Clamping keeps them readable
but throws away the tail -- for an alert, usually the part that matters. So the
text is MEASURED against that client's screen, split into segments that each fit,
and advanced on a tick.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural.gui import overlay as OV
from sbs_utils.procedural.gui.overlay import (
    overlay_banner, overlay_lower_third, overlay_clear, _auto_dwell,
    DWELL_MIN, DWELL_MAX)


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)
        self.vars = {}

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


class CycleBase(unittest.TestCase):
    """Pins the measurement so the tests describe BEHAVIOUR, not a font metric:
    a 'word' is 10px wide and the strip is 100px, so ~9 words fit per segment."""

    SLOT_PX = 100.0

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = 0
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(0)
        client.page_stack.append(self.page)
        FrameContext.page = self.page

        self._real_width = OV._slot_px_width
        OV._slot_px_width = lambda cid, slot, pad=0.96: self.SLOT_PX
        self._real_split = OV._split_to_fit

        def _fake_split(cid, slot, text, font, width_frac=1.0):
            words = " ".join(str(text or "").split()).split()
            if not words:
                return [""]
            # width_frac: a kind that spends part of the strip on something else
            # (a portrait) measures against what is LEFT.
            per = max(1, int((self.SLOT_PX * width_frac) // 10))
            return [" ".join(words[i:i + per]) for i in range(0, len(words), per)]

        OV._split_to_fit = _fake_split

    def tearDown(self):
        OV._slot_px_width = self._real_width
        OV._split_to_fit = self._real_split
        FrameContext.page = None
        FrameContext.context = None
        Agent.clear()
        SpaceObject.clear()

    def slot(self, name="top_banner"):
        return self.page.overlays.slots.get(name)

    def shown(self, name="top_banner", field="text"):
        r = self.slot(name)
        return None if r is None or r.content is None else r.content.get(field)

    def tick(self):
        """Fire the pending interval task once."""
        for t in list(TickDispatcher._new_this_tick):
            t.cb(t)


class TestFitsUnchanged(CycleBase):
    def test_short_text_shows_whole_and_schedules_nothing(self):
        overlay_banner("RED ALERT")
        self.assertEqual(self.shown(), "RED ALERT")
        self.assertEqual(len(TickDispatcher._new_this_tick), 0, "no cycle needed")

    def test_cycle_false_leaves_long_text_whole(self):
        long = " ".join(f"w{i}" for i in range(30))
        overlay_banner(long, cycle=False)
        self.assertEqual(self.shown(), long)
        self.assertEqual(len(TickDispatcher._new_this_tick), 0)


class TestSplitAndCycle(CycleBase):
    def test_long_text_starts_on_its_first_part(self):
        long = " ".join(f"w{i}" for i in range(30))
        overlay_banner(long)
        first = self.shown()
        self.assertNotEqual(first, long, "shows a part, not the whole line")
        self.assertTrue(long.startswith(first))
        self.assertEqual(len(TickDispatcher._new_this_tick), 1, "one cycle task")

    def test_advances_to_the_next_part(self):
        long = " ".join(f"w{i}" for i in range(30))
        overlay_banner(long)
        first = self.shown()
        self.tick()
        self.assertNotEqual(self.shown(), first, "moved on")
        self.assertIn(self.shown(), long)

    def test_no_word_is_lost_across_the_parts(self):
        words = [f"w{i}" for i in range(30)]
        overlay_banner(" ".join(words))
        seen = self.shown().split()
        for _ in range(10):
            self.tick()
            cur = self.shown()
            if cur is None:
                break
            seen.extend(cur.split())
        for w in words:
            self.assertIn(w, seen, f"{w} was dropped")

    def test_plays_once_then_clears_when_it_has_a_lifetime(self):
        overlay_banner(" ".join(f"w{i}" for i in range(20)), seconds=30)
        for _ in range(6):
            self.tick()
        r = self.slot()
        self.assertTrue(r is None or r.is_empty, "sequence ends by clearing")

    def test_sticky_banner_loops(self):
        overlay_banner(" ".join(f"w{i}" for i in range(20)))   # no seconds -> sticky
        for _ in range(8):
            self.tick()
        self.assertIsNotNone(self.shown(), "still cycling")

    def test_a_newer_banner_stops_the_old_cycle(self):
        overlay_banner(" ".join(f"w{i}" for i in range(30)))
        overlay_banner("TAKEOVER")                 # claims the slot
        self.assertEqual(self.shown(), "TAKEOVER")
        self.tick()                                # the stale cycle must not repaint
        self.assertEqual(self.shown(), "TAKEOVER")

    def test_clearing_stops_the_cycle(self):
        overlay_banner(" ".join(f"w{i}" for i in range(30)))
        overlay_clear("top_banner")
        self.tick()
        r = self.slot()
        self.assertTrue(r is None or r.is_empty, "cycle does not resurrect a cleared slot")


class TestLowerThirdCycles(CycleBase):
    def test_long_line_splits_and_keeps_the_name(self):
        overlay_lower_third("Admiral Harkin", " ".join(f"w{i}" for i in range(30)))
        r = self.slot("lower_third")
        self.assertEqual(r.content["name"], "Admiral Harkin")
        self.assertNotIn("w29", r.content["line"], "first part only")
        self.assertEqual(len(TickDispatcher._new_this_tick), 1)

    def test_subtitles_do_not_loop(self):
        overlay_lower_third("Admiral", " ".join(f"w{i}" for i in range(20)))
        for _ in range(6):
            self.tick()
        r = self.slot("lower_third")
        self.assertTrue(r is None or r.is_empty, "a repeating subtitle reads as a stutter")


class TestDwell(CycleBase):
    def test_dwell_is_paced_by_length_within_bounds(self):
        short = _auto_dwell("two words")
        long = _auto_dwell(" ".join(["word"] * 30))
        self.assertLessEqual(short, long)
        for d in (short, long):
            self.assertGreaterEqual(d, DWELL_MIN)
            self.assertLessEqual(d, DWELL_MAX)

    def test_explicit_dwell_is_used(self):
        overlay_banner(" ".join(f"w{i}" for i in range(30)), dwell=1.0)
        t = next(iter(TickDispatcher._new_this_tick))
        self.assertEqual(t.delay, 1.0)


class TestMeasurementFallback(CycleBase):
    def test_unmeasurable_text_is_left_whole(self):
        # restore the real splitter, then make measurement unavailable
        OV._split_to_fit = self._real_split
        OV._slot_px_width = lambda cid, slot, pad=0.96: None
        long = " ".join(f"w{i}" for i in range(30))
        overlay_banner(long)
        self.assertEqual(self.shown(), long, "no measurement -> behave as before")
        self.assertEqual(len(TickDispatcher._new_this_tick), 0)


if __name__ == "__main__":
    unittest.main()
