"""What the crew actually reads when a boarding room reaches the PADD.

Everything here was found the first time anybody LOOKED at the real screens (the engine,
2026-10-03, a mission made from the starter template). Scripts had driven the same visit
to the end many times and seen none of it, because a script reads the model:

  * the room was filed under its KEY - `airlock`, under a heading that says
    `The Airlock` - and signed "Away", the module's old name;
  * a room offers more replies than a letter does, the band held three, and the fourth
    was drawn under the compose line where a click on it landed in the text box;
  * the last reply of every stack was half the width of the others, because the
    region's placeholder was a second cell on its row;
  * the PADD's bar named the console `BOARDING_CREW`.

    python -m unittest tests.test_boarding_room_on_screen
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401 - import first, breaks a circular import
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural import boarding as B
from sbs_utils.procedural.gui import messages_gui as M
from sbs_utils.procedural.gui.epadd import epadd_console_title
from sbs_utils.procedural.messages import message_inbox


class _Sim:
    time_tick_counter = 0


def _rooms():
    return {"airlock": {"key": "airlock", "display_text": "The Airlock", "data": {},
                        "children": [],
                        "description": "% The outer door was never sealed.\n\n"
                                       "- [Go aft](airlock)\n- [Return to the ship]()\n"}}


class Base(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_Sim(), sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        clear_shared()
        B.boarding_clear()
        B._TEAM.clear()
        self.addCleanup(B.boarding_clear)
        self.addCleanup(B._TEAM.clear)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None


class TheRoomIsNamedTests(Base):
    def test_the_subject_is_the_rooms_name_not_its_key(self):
        B.boarding_scene_begin(_rooms(), "airlock")
        msg = message_inbox("boarding")[0]
        self.assertEqual(msg["subject"], "The Airlock")
        self.assertEqual(msg["scene"], "airlock")       # the key is still what it is filed by

    def test_a_room_with_no_name_falls_back_to_its_key(self):
        rooms = _rooms()
        rooms["airlock"]["display_text"] = ""
        B.boarding_scene_begin(rooms, "airlock")
        self.assertEqual(message_inbox("boarding")[0]["subject"], "airlock")

    def test_a_speaker_still_signs_their_own_line(self):
        B.boarding_scene_begin(_rooms(), "airlock", speaker="The Keeper")
        self.assertEqual(message_inbox("boarding")[0]["from"], "The Keeper")

    def test_narration_is_signed_by_the_place(self):
        Agent.SHARED.set_inventory_value(B.INVITE_KEY, {"open": True, "title": "The Hulk",
                                                         "roster": [], "reserved": {}})
        B.boarding_scene_begin(_rooms(), "airlock")
        self.assertEqual(message_inbox("boarding")[0]["from"], "The Hulk")

    def test_narration_with_no_place_is_never_signed_away(self):
        B.boarding_scene_begin(_rooms(), "airlock")
        self.assertNotEqual(message_inbox("boarding")[0]["from"], "Away")


class TheReplyBandTests(unittest.TestCase):
    """The band is a region pinned above the compose line; whatever is drawn in it has to
    FIT in it, because the engine does not clip and a button under the compose line
    cannot be pressed."""

    def rows(self, count):
        import sbs_utils.procedural.gui.row as row_mod
        import sbs_utils.procedural.gui.blank as blank_mod
        drawn = []
        real_row, real_blank = row_mod.gui_row, blank_mod.gui_blank
        row_mod.gui_row = lambda style="": drawn.append(style)
        blank_mod.gui_blank = lambda *a, **k: None
        try:
            each = M._reply_rows_begin(count)
        finally:
            row_mod.gui_row, blank_mod.gui_blank = real_row, real_blank
        return drawn, each

    @staticmethod
    def px(style):
        import re
        height = int(re.search(r"row-height: (\d+)px", style).group(1))
        pad = 6 if "padding" in style else 0
        return height + pad

    def test_the_band_holds_a_rooms_worth_of_replies(self):
        # A way on, a way back, a way home, and one reading per job: six for a lone
        # officer in a room written for four jobs.
        self.assertGreaterEqual(M.REPLY_ROWS, 6)

    def test_a_stack_always_fits_the_band(self):
        for count in (1, 2, 3, 4, 6, 7, 9, 12):
            spacer, each = self.rows(count)
            total = sum(self.px(s) for s in spacer) + count * self.px(each)
            self.assertLessEqual(total, M.REPLY_BAND_PX, count)

    def test_a_short_stack_sits_at_the_bottom(self):
        spacer, each = self.rows(2)
        self.assertEqual(len(spacer), 1)                  # one blank row above the buttons
        total = self.px(spacer[0]) + 2 * self.px(each)
        self.assertGreaterEqual(total, M.REPLY_BAND_PX - 12)

    def test_a_full_stack_needs_no_spacer(self):
        spacer, _each = self.rows(M.REPLY_ROWS)
        self.assertEqual(spacer, [])

    def test_the_placeholder_has_a_row_of_its_own(self):
        """It used to share the last reply's row, which halved that button."""
        import inspect
        src = inspect.getsource(M._reading_replies_fill)
        self.assertLess(src.index("_reply_strip(reading)"), src.index("gui_row("))
        self.assertLess(src.index("gui_row("), src.rindex("gui_text("))


class TheBarNamesTheConsoleTests(unittest.TestCase):
    def test_a_boarded_console_is_named_in_words(self):
        self.assertEqual(epadd_console_title("boarding_crew"), "boarding party")

    def test_no_title_ever_carries_an_underscore(self):
        for console in ("boarding_crew", "normal_helm", "gamemaster_overseer_comms", "helm"):
            self.assertNotIn("_", epadd_console_title(console), console)

    def test_an_ordinary_console_keeps_its_name(self):
        self.assertEqual(epadd_console_title("engineering"), "engineering")
        self.assertEqual(epadd_console_title(None), "")


if __name__ == "__main__":
    unittest.main()
