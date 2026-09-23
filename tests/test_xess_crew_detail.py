"""xESS Crew detail: the caller's face leads their name, a Room row, then what they said
- one text area (procedural/gui/xess.py `_caller_detail_text`)."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from unittest import mock

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.gui import xess as X
from sbs_utils.pages.layout.text_area import TextArea, IconLine, TableLine, TextLine
from sbs_utils.pages.layout.layout import Bounds

FACE = "ter #ffffff 1 2"


class TestCrewDetail(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _parse(self, text):
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 40, 80)
        ta.calc_rich(0)
        return ta

    def test_a_person_leads_with_their_face(self):
        item = {"id": 7, "name": "Lt Marek", "job": "medic", "room": "Engineering"}
        with mock.patch("sbs_utils.faces.get_face", return_value=FACE):
            ta = self._parse(X._caller_detail_text(item, {"text": "Hull breach on deck 2."}))
        lead = [ln for ln in ta.lines if isinstance(ln, IconLine)][0]
        self.assertEqual((lead.ns, lead.urn, lead.text), ("face", FACE, "Lt Marek - medic"))
        grid = [ln for ln in ta.lines if isinstance(ln, TableLine)][0]
        self.assertEqual(grid.rows, [["Room", "Engineering"]])
        self.assertTrue(any(isinstance(ln, TextLine) and "Hull breach" in ln.text for ln in ta.lines))

    def test_the_ship_row_has_no_face(self):
        item = {"id": "ship", "name": "Artemis", "job": "ship", "room": ""}
        text = X._caller_detail_text(item, None)
        self.assertNotIn("face://", text)
        self.assertIn("Artemis - ship", text)
        self.assertIn("Nothing said yet.", text)
        self.assertNotIn("| Room", text)

    def test_no_face_on_file_is_just_the_name(self):
        item = {"id": 7, "name": "Vex", "job": "pilot", "room": ""}
        with mock.patch("sbs_utils.faces.get_face", return_value=""):
            self.assertTrue(X._caller_detail_text(item, None).startswith("Vex - pilot"))

    def test_a_pipe_cannot_split_the_room_row(self):
        item = {"id": "ship", "name": "A", "job": "b", "room": "Cargo | Bay"}
        self.assertIn("| Room | Cargo / Bay |", X._caller_detail_text(item, None))


if __name__ == "__main__":
    unittest.main()
