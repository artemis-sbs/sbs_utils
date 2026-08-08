"""A caller-supplied `line_styles` must reach the text, in either markdown mode.

`line_styles` used to be read only when `markdown=False`, so in the default mode every
caller style was silently discarded - including the callout styles that are the DOCUMENTED
way to render a callout:

    body, styles = amd_callout_render(record.get("body"))
    gui_text_area(body, line_styles=styles)

`amd_callout` had no caller but the log panel, so nothing had ever exercised it. The
symptom was a waterfall message's color not surviving into the log.

COVERAGE HONESTY: these tests pin the style SHAPE and the store -> styles path end to end.
They do NOT cover the markdown gate itself - that lives in the render loop, which needs
bounds and a client to reach, and it is verified by reading. A test here passes with the
fix reverted, so do not read it as a regression guard for that line.

    python -m unittest tests.test_text_area_line_styles
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.pages.layout.text_area import TextArea


RED = {"style": "color:#f00;"}


class LineStyleTests(unittest.TestCase):
    def _area(self, text, styles, markdown):
        return TextArea("t", text, markdown=markdown, line_styles=styles)

    def test_normalised_shape_fills_the_gaps(self):
        """A caller passes only what it cares about; the rest is defaulted."""
        ta = self._area("one", [RED], markdown=False)
        st = ta.line_style_for(0)
        self.assertIn("color:#f00;", st["style"])
        for key in ("prepend", "indent", "background"):
            self.assertIn(key, st, f"{key} should be defaulted for the renderer")

    def test_the_style_is_available_in_markdown_mode(self):
        """NOTE this does NOT cover the fix. `line_style_for` was never the broken part -
        it always returned the caller's style. The bug was in the RENDER LOOP
        (`calc_rich`), which only consulted it when `markdown` was False and otherwise
        threw it away. Reaching that loop needs bounds and a client, so the gate itself is
        verified by reading, not here. This pins the accessor the loop depends on."""
        ta = self._area("one", [RED], markdown=True)
        self.assertIsNotNone(ta.line_style_for(0))
        self.assertIn("color:#f00;", ta.line_style_for(0)["style"])

    def test_none_slots_stay_none(self):
        """A line the caller did not style must render normally, not forced white."""
        ta = self._area("one\ntwo", [None, RED], markdown=True)
        self.assertIsNone(ta.line_style_for(0))
        self.assertIsNotNone(ta.line_style_for(1))

    def test_out_of_range_is_safe(self):
        ta = self._area("one\ntwo\nthree", [RED], markdown=True)
        self.assertIsNone(ta.line_style_for(2))

    def test_no_styles_at_all_is_safe(self):
        ta = self._area("one", None, markdown=True)
        self.assertIsNone(ta.line_style_for(0))


class LogPanelStylesReachTheWidgetTests(unittest.TestCase):
    """End to end: what comms_broadcast stored must be styled in the widget."""

    def test_a_broadcast_color_survives_into_the_log(self):
        from sbs_utils.procedural import log_panel as LP
        LP.log_clear()
        LP.log_add(1, "Red alert!", color="red")
        text, styles = LP.log_render(LP.log_entries(1))
        ta = TextArea("t", text, markdown=False, line_styles=styles)
        self.assertIn("color:red;", ta.line_style_for(0)["style"],
                      "the waterfall's color must reach the new text")

    def test_a_severity_callout_survives_into_the_log(self):
        from sbs_utils.procedural import log_panel as LP
        LP.log_clear()
        LP.log_add(1, "Hull breach", severity="danger")
        text, styles = LP.log_render(LP.log_entries(1))
        ta = TextArea("t", text, markdown=False, line_styles=styles)
        self.assertTrue(ta.line_style_for(0)["background"], "the callout box must survive")
