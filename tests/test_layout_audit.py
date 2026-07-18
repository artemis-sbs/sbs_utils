"""Deterministic precision/recall for the GUI layout audit (gui-sizing-accuracy).

The audit is only worth building if it flags REAL overflow/overlap and stays quiet
on clean layouts. These tests feed the LayoutAudit synthetic widget streams with
KNOWN-good and KNOWN-bad geometry (ground truth we author) and assert exactly what
it flags — no engine, no browser, no eyes. Pure geometry: layout_audit imports
nothing external, so this is a fast white-box check.
"""
import unittest

from cosmos_dev.layout_audit import LayoutAudit


def _kinds(a):
    return sorted(k for k, _ in a._findings.values())


class TestLayoutAudit(unittest.TestCase):
    def setUp(self):
        self.a = LayoutAudit()

    # -- recall: real bugs ARE flagged --------------------------------------
    def test_overflow_bottom_spill(self):
        # the real LM checkbox case: rect bottom past the region floor
        self.a.record("send_gui_checkbox", 0, "reg$$", "cb", 0, 0, 89.14, 11.72, 100.86)
        self.a.complete(0, "reg$$")
        self.assertIn("OVERFLOW", _kinds(self.a))

    def test_overflow_negative_left(self):
        self.a.record("send_gui_text", 0, "root", "t", 0, -3, 0, 20, 10)
        self.a.complete(0, "root")
        self.assertIn("OVERFLOW", _kinds(self.a))

    def test_overlap_same_layer_content(self):
        self.a.record("send_gui_text", 0, "root", "t1", 0, 0, 0, 50, 10)
        self.a.record("send_gui_text", 0, "root", "t2", 0, 30, 0, 80, 10)  # x 30-50 overlap
        self.a.complete(0, "root")
        self.assertIn("OVERLAP", _kinds(self.a))

    def test_degenerate_inverted_rect(self):
        self.a.record("send_gui_text", 0, "root", "t", 0, 50, 10, 40, 20)  # right < left
        self.a.complete(0, "root")
        self.assertIn("DEGENERATE", _kinds(self.a))

    # -- precision: clean / intentional layouts are NOT flagged --------------
    def test_clean_layout_silent(self):
        self.a.record("send_gui_text", 0, "root", "t1", 0, 0, 0, 40, 10)
        self.a.record("send_gui_text", 0, "root", "t2", 0, 50, 0, 90, 10)  # no overlap
        self.a.complete(0, "root")
        self.assertEqual(self.a._findings, {})

    def test_touching_edge_within_slop(self):
        # a rect that just reaches 100 (+ tiny slop) is not an overflow
        self.a.record("send_gui_text", 0, "root", "t", 0, 0, 0, 100.2, 10)
        self.a.complete(0, "root")
        self.assertEqual(self.a._findings, {})

    def test_overlap_ignored_across_draw_layers(self):
        # deliberate layering (different draw_layer) is not a collision
        self.a.record("send_gui_text", 0, "root", "t1", 0, 0, 0, 50, 10)
        self.a.record("send_gui_text", 0, "root", "t2", 5, 30, 0, 80, 10)
        self.a.complete(0, "root")
        self.assertNotIn("OVERLAP", _kinds(self.a))

    def test_overlap_ignored_background_image(self):
        # text sitting on a background image is intended, not a collision
        self.a.record("send_gui_image", 0, "root", "bg", 0, 0, 0, 100, 100)
        self.a.record("send_gui_text", 0, "root", "t", 0, 10, 10, 40, 20)
        self.a.complete(0, "root")
        self.assertNotIn("OVERLAP", _kinds(self.a))

    # -- robustness ----------------------------------------------------------
    def test_dedup_across_frames(self):
        # the dirty system re-emits every tick; one bug must not accumulate
        for _ in range(5):
            self.a.record("send_gui_checkbox", 0, "reg", "cb", 0, 0, 89, 12, 100.9)
            self.a.complete(0, "reg")
        overflows = [k for k, _ in self.a._findings.values() if k == "OVERFLOW"]
        self.assertEqual(len(overflows), 1)

    def test_clear_removes_region_before_audit(self):
        # a region cleared before complete leaves no stale widgets to flag
        self.a.record("send_gui_text", 0, "reg", "t", 0, -5, 0, 20, 10)  # would overflow
        self.a.clear(0, "reg")
        self.a.complete(0, "reg")
        self.assertEqual(self.a._findings, {})

    def test_per_client_isolation(self):
        # a bug on client 1 is not attributed to a clean client 2
        self.a.record("send_gui_text", 1, "root", "bad", 0, 0, 0, 20, 105)  # overflow
        self.a.record("send_gui_text", 2, "root", "ok", 0, 0, 0, 20, 10)
        self.a.complete(1, "root")
        self.a.complete(2, "root")
        self.assertEqual(_kinds(self.a), ["OVERFLOW"])


if __name__ == "__main__":
    unittest.main()
