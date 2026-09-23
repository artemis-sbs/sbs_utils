"""The xESS Scan readout: a condition pip and an INVERTED wear gauge, as text-area
markdown (the same text is filed to the survey log)."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from unittest import mock

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural import internal_damage as D
from sbs_utils.pages.layout.text_area import TextArea, IconLine, GaugeLine
from sbs_utils.pages.layout.layout import Bounds
from sbs_utils.pages.layout.gauge import gauge_color, COLOR_OK, COLOR_WARN, COLOR_CRIT


class TestScanReadout(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _read(self, state, wear):
        with mock.patch.object(D, "grid_node_state", return_value=state), \
             mock.patch.object(D, "grid_node_wear", return_value=wear):
            text = X._condition(object())
        ta = TextArea("t", "## Room\n" + text)
        ta.bounds = Bounds(0, 0, 40, 60)
        ta.calc_rich(0)
        pip = [ln for ln in ta.lines if isinstance(ln, IconLine)][0]
        gauge = [ln for ln in ta.lines if isinstance(ln, GaugeLine)][0]
        return text, pip, gauge

    def test_worn_room(self):
        text, pip, gauge = self._read("worn", 0.7)
        self.assertEqual(pip.text, "Worn")
        self.assertIn("Gold", pip.urn)
        self.assertEqual(gauge.spec["label"], "Wear")
        self.assertTrue(gauge.spec["invert"])
        self.assertEqual(gauge_color(gauge.spec), COLOR_WARN)     # past the worn line
        self.assertNotIn("%", text.split("\n")[0])                # no hand-made percent

    def test_fresh_and_nearly_worn_out(self):
        self.assertEqual(gauge_color(self._read("nominal", 0.25)[2].spec), COLOR_OK)
        self.assertEqual(gauge_color(self._read("worn", 0.9)[2].spec), COLOR_CRIT)

    def test_tuned_is_cyan(self):
        _, pip, gauge = self._read("tuned", 0.05)
        self.assertEqual(gauge_color(gauge.spec), "#40E0E0")
        self.assertEqual(pip.text, "Tuned")

    def test_the_condition_word_is_not_heading_sized(self):
        """`## Room` then the pip line: without a blank line between them the pip line
        inherits the heading's font (engine-seen). The pip line must use body text."""
        from sbs_utils.helpers import split_props
        with mock.patch.object(D, "grid_node_state", return_value="nominal"), \
             mock.patch.object(D, "grid_node_wear", return_value=0.25):
            text = "\n".join(["## arrival", "", X._condition(object())])
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 40, 60)
        ta.calc_rich(0)
        pip = [ln for ln in ta.lines if isinstance(ln, IconLine)][0]
        self.assertEqual(pip.font, "gui-2")

    def test_the_scan_app_puts_a_blank_line_after_the_heading(self):
        import inspect
        self.assertIn('boarding_room_name(room.name), "", _condition(room)', inspect.getsource(X._scan_app))

    def test_no_reading(self):
        with mock.patch.object(D, "grid_node_state", side_effect=RuntimeError):
            self.assertEqual(X._condition(object()), "No condition reading.")


if __name__ == "__main__":
    unittest.main()
