"""Gauges: `[Label](gauge://v?max=m)` in gui_text_area (block line + table cell),
the shared drawer, and the AMD block the tooling sees."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.gui import get_client_aspect_ratio
from sbs_utils.pages.layout.text_area import TextArea, TableLine, GaugeLine, TextLine
from sbs_utils.pages.layout.layout import Bounds
from sbs_utils.pages.layout.gauge import (gauge_spec, gauge_spec_from_url, gauge_color,
                                          gauge_fraction, gauge_value_text, gauge_send,
                                          COLOR_OK, COLOR_WARN, COLOR_CRIT, COLOR_TRACK)
from sbs_utils.procedural.amd_blocks import amd_blocks_text


class _Rec:
    """Records send_gui_* calls."""
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("send_gui_"):
            return lambda *a: self.calls.append((name, a))
        raise AttributeError(name)


class TestGaugeSpec(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(gauge_color(gauge_spec(946, 1000)), COLOR_OK)
        self.assertEqual(gauge_color(gauge_spec(45, 120)), COLOR_WARN)   # 0.375
        self.assertEqual(gauge_color(gauge_spec(12, 120)), COLOR_CRIT)   # 0.1
        self.assertEqual(gauge_color(gauge_spec(12, 120, color="#fff")), "#fff")

    def test_over_max_is_the_tuned_cyan(self):
        from sbs_utils.pages.layout.gauge import COLOR_OVER
        from sbs_utils.procedural.grid import GRID_TUNED_COLOR
        self.assertEqual(COLOR_OVER, GRID_TUNED_COLOR)        # one color, two places
        self.assertEqual(gauge_color(gauge_spec(110, 100)), COLOR_OVER)
        self.assertEqual(gauge_fraction(gauge_spec(110, 100)), 1.0)
        self.assertEqual(gauge_color(gauge_spec(100, 100)), COLOR_OK)   # AT max is green
        self.assertEqual(gauge_color(gauge_spec(110, 100, color="#fff")), "#fff")
        self.assertEqual(gauge_value_text(gauge_spec(120, 100, show="pct")), "120%")

    def test_invert_more_is_worse(self):
        from sbs_utils.pages.layout.gauge import gauge_spec_from_url
        self.assertEqual(gauge_color(gauge_spec(0.1, 1, invert=True)), COLOR_OK)     # little wear
        self.assertEqual(gauge_color(gauge_spec(0.6, 1, invert=True)), COLOR_WARN)   # 0.4 left
        self.assertEqual(gauge_color(gauge_spec(0.9, 1, invert=True)), COLOR_CRIT)   # 0.1 left
        self.assertEqual(gauge_color(gauge_spec(1.2, 1, invert=True)), COLOR_CRIT)   # over: red, not cyan
        self.assertEqual(gauge_fraction(gauge_spec(0.6, 1, invert=True)), 0.6)       # bar still grows
        self.assertTrue(gauge_spec_from_url("0.6?max=1&invert=1")["invert"])
        self.assertFalse(gauge_spec_from_url("0.6?max=1&invert=0")["invert"])

    def test_out_of_range_clamps_bar_not_number(self):
        s = gauge_spec(-45, 8, "Homing", show="frac")
        self.assertEqual(gauge_fraction(s), 0.0)
        self.assertEqual(gauge_value_text(s), "-45 / 8")
        self.assertEqual(gauge_fraction(gauge_spec(20, 8)), 1.0)

    def test_show_defaults(self):
        self.assertEqual(gauge_spec(5, 10, "Energy")["show"], "value")
        self.assertEqual(gauge_spec(5, 10)["show"], "none")
        self.assertEqual(gauge_value_text(gauge_spec(1, 4, show="pct")), "25%")

    def test_bad_numbers_do_not_raise(self):
        s = gauge_spec_from_url("abc?max=zz&warn=q")
        self.assertEqual((s["value"], s["max"], s["warn"]), (0.0, 100.0, 0.5))
        self.assertEqual(gauge_fraction(gauge_spec(5, 0)), 0.0)


class TestGaugeDraw(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.ar = get_client_aspect_ratio(0)

    def test_fill_and_track_do_not_overlap(self):
        rec = _Rec()
        gauge_send(rec, 0, "r", "g", 10, 10, 50, 14, gauge_spec(45, 120, "FRNT SHLD"), self.ar)
        imgs = {a[2]: a for n, a in rec.calls if n == "send_gui_image"}
        fill, track = imgs["g:f"], imgs["g:t"]
        self.assertIn(COLOR_WARN, fill[3])
        self.assertIn(COLOR_TRACK, track[3])
        self.assertAlmostEqual(fill[6], track[4])            # fill.right == track.left
        self.assertAlmostEqual(fill[6], 10 + 40 * 45 / 120)
        texts = [a[3] for n, a in rec.calls if n == "send_gui_text"]
        self.assertTrue(any("FRNT SHLD" in t and "justify:left" in t for t in texts))
        self.assertTrue(any("45" in t and "justify:right" in t for t in texts))

    def test_both_rects_are_sent_even_at_zero_width(self):
        """A self-updating gauge re-sends out of band, where the engine only updates
        widgets that were in the build - so an empty fill must still be SENT at build
        time, or it can never appear (engine-seen: a build bar that never filled)."""
        for value in (0, 8):                                   # empty, and full
            rec = _Rec()
            gauge_send(rec, 0, "r", "g", 0, 0, 50, 4, gauge_spec(value, 8), self.ar)
            self.assertEqual(sorted(a[2] for n, a in rec.calls), ["g:f", "g:t"])


class TestGaugeWidgetDirty(unittest.TestCase):
    """A gauge repaints itself only at top level. In a sub-region the engine overdraws
    re-sent text (engine-seen 2026-09-23), so it must leave the repaint to the owner."""
    def setUp(self):
        from sbs_utils.pages.layout.dirty import Dirty
        self.Dirty = Dirty
        Dirty.dirty = {}

    def _gauge(self, region_tag):
        from sbs_utils.pages.layout.gauge import Gauge
        g = Gauge("g", 10, 100, "Energy")
        g.client_id = 0
        g.region_tag = region_tag
        return g

    def test_top_level_marks_itself(self):
        g = self._gauge("")
        g.value = 50
        self.assertIn(g, self.Dirty.dirty.get(0, set()))

    def test_in_region_sends_nothing(self):
        g = self._gauge("ovl_status$$")
        g.value = 50
        self.assertEqual(self.Dirty.dirty.get(0, set()), set())
        self.assertEqual(g.spec()["value"], 50.0)          # the value still changed


class TestTextAreaGauge(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _calc(self, text, markdown=True):
        ta = TextArea("t", text, markdown=markdown)
        ta.bounds = Bounds(0, 0, 40, 80)
        ta.calc_rich(0)
        return ta

    def test_whole_line_gauge(self):
        ta = self._calc("# Status\n[Energy](gauge://946?max=1000)\n[](gauge://45?max=120)")
        gauges = [ln for ln in ta.lines if isinstance(ln, GaugeLine)]
        self.assertEqual(len(gauges), 2)
        self.assertEqual(gauges[0].spec["label"], "Energy")
        self.assertEqual(gauges[1].spec["show"], "none")
        self.assertTrue(all(g.height > 0 for g in gauges))

    def test_markdown_off_is_text(self):
        ta = self._calc("[Energy](gauge://946?max=1000)\nnext", markdown=False)
        self.assertFalse(any(isinstance(ln, GaugeLine) for ln in ta.lines))

    def test_gauge_grid_in_table_without_header(self):
        md = ("| | |\n"
              "|:--:|:--:|\n"
              "| [ENGN](gauge://1?max=1&show=none) | [WEAP](gauge://0.2?max=1&show=none) |\n"
              "| [SHLD](gauge://1?max=1&show=none) | [SENS](gauge://0.4?max=1&show=none) |")
        ta = self._calc(md)
        t = [ln for ln in ta.lines if isinstance(ln, TableLine)][0]
        self.assertFalse(t.has_header)
        self.assertEqual(len(t.rows), 2)
        self.assertEqual(len(t.gauges), 4)
        rec = _Rec()
        t.send_gui(rec, 0, "r", "tb", 0, 0, 40, 20)
        fills = [a for n, a in rec.calls if n == "send_gui_image" and a[2].endswith(":f")]
        self.assertEqual(len(fills), 4)
        self.assertTrue(any(COLOR_CRIT in a[3] for a in fills))     # WEAP 0.2
        centred = [a[3] for n, a in rec.calls if n == "send_gui_text"]
        self.assertTrue(all("justify:center" in s for s in centred))
        # A bar is as long as it is given: gauge columns take the spare width, so the
        # grid spans the area instead of being as narrow as "ENGN".
        ar = get_client_aspect_ratio(0)
        full_px = (ta.bounds.right - ta.bounds.left) / 100 * ar.x
        self.assertAlmostEqual(sum(t.col_px) + t.cell_pad_px, full_px, delta=1.0)

    def test_table_mixes_text_and_gauge_cells(self):
        md = ("| System | Level |\n"
              "|:--|:--|\n"
              "| Shields | [](gauge://45?max=120) |")
        t = [ln for ln in self._calc(md).lines if isinstance(ln, TableLine)][0]
        self.assertTrue(t.has_header)
        self.assertEqual(list(t.gauges), [(1, 1)])


class TestAmdGaugeBlock(unittest.TestCase):
    def test_block(self):
        blocks = amd_blocks_text("[Energy](gauge://946?max=1000&show=frac)")
        g = [b for b in blocks if b.get("type") == "gauge"]
        self.assertEqual(len(g), 1)
        self.assertEqual((g[0]["label"], g[0]["value"], g[0]["max"]), ("Energy", "946", "1000"))
        self.assertEqual(g[0]["options"], {"show": "frac"})
        self.assertFalse(any(b.get("type") == "media" for b in blocks))


if __name__ == "__main__":
    unittest.main()
