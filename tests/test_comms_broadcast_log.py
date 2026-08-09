"""comms_broadcast -> log colors, through the REAL entry point (mkdocs build/messages.md).

Two colour regressions came from testing below this line. The store and renderer were
tested directly, so both passed while the actual path was broken:

* `line_styles` was discarded whenever markdown was on (the widget's default), so no
  style reached the screen at all.
* `comms_broadcast` defaulted `color` to "#fff" BEFORE handing the entry to the log, so
  every entry looked like it had asked to be white and a category tint could never show.

Neither was visible from a test that called `log_add` directly. These go through
comms_broadcast and assert on what the WIDGET would use.

    python -m unittest tests.test_comms_broadcast_log
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.comms import comms_broadcast
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural import log_panel as LP
from sbs_utils.pages.layout.text_area import TextArea


class BroadcastColorTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        LP.log_clear()
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))

    def _styles(self):
        """The styles the WIDGET would use - not the ones the renderer emitted."""
        text, styles = LP.log_render(LP.log_entries(self.ship))
        ta = TextArea("t", text, markdown=False, line_styles=styles)
        return [ta.line_style_for(i) for i in range(len(text.splitlines()))]

    def test_an_explicit_color_reaches_the_widget(self):
        comms_broadcast(self.ship, "Red alert!", "red")
        self.assertIn("color:red;", self._styles()[0]["style"])

    def test_no_color_given_is_not_forced_white(self):
        """The engine still gets its "#fff" default; the LOG must see that nobody asked,
        or a category tint can never win. (The line still carries a FONT - log text runs a
        size down from document text - so assert on the colour, not on the slot.)"""
        comms_broadcast(self.ship, "plain")
        style = self._styles()[0]["style"]
        self.assertNotIn("color:", style,
                         "an uncolored message must not be forced to a colour")

    def test_a_category_tints_the_line(self):
        comms_broadcast(self.ship, "docked at DS 1", category="ship")
        self.assertIn(LP.CATEGORY_COLOR["ship"], self._styles()[0]["style"])

    def test_an_explicit_color_still_beats_the_category(self):
        comms_broadcast(self.ship, "urgent", "red", category="ship")
        self.assertIn("color:red;", self._styles()[0]["style"])

    def test_severity_draws_a_box(self):
        comms_broadcast(self.ship, "Hull breach", category="ship", severity="danger")
        self.assertTrue(self._styles()[0]["background"])

    def test_the_engine_still_gets_its_default_color(self):
        """Preserving the caller's None must not change what the waterfall receives."""
        sent = []
        real = sbs.send_message_to_player_ship
        sbs.send_message_to_player_ship = lambda sid, color, msg: sent.append(color)
        try:
            comms_broadcast(self.ship, "plain")
        finally:
            sbs.send_message_to_player_ship = real
        self.assertEqual(["#fff"], sent)
