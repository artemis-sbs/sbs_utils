"""A DOWNED crew member chooses nothing - engine-seen, author course 3 lesson 14.

Dr Hale went DOWN at the yard terminal with its scene open on her xESS (bar `DOWN -
needs a medkit`, figure lying), and her Act page still took `Copy it down` and `Send the
sentry its recognition update` - and the update RAN: the power cell was given, the sentry
calmed. A press by somebody lying on the floor applied its outcome.

THE RULE: a downed character's presses do nothing, her open scene says she is down in
place of her choices, and getting back up gives the choices back.

    python -m unittest tests.test_boarding_down_cannot_choose
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.pages.layout.text_area import TextArea
from sbs_utils.pages.layout.bounds import Bounds

HALE = 0x8000000000000071
REYES = 0x8000000000000072

TERMINAL = (
    "% DOOR SEALED. AWAITING CODE.\n"
    "- [Send the sentry its recognition update](update)\n"
    "- [Step back]()\n"
)


def _scenes():
    def node(key, body):
        return {"key": key, "display_text": key, "description": body, "data": {}}
    return {"terminal": node("terminal", TERMINAL),
            "update": node("update", "% The sentry stops.\n")}


class ADownedMemberChoosesNothing(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        SpaceObject.clear()
        self._prev_metric = D._METRIC_RESOLVER
        self.addCleanup(D.dialogue_set_metric_resolver, self._prev_metric)
        for clear in (A.boarding_clear, K.boarding_combat_clear):
            clear()
            self.addCleanup(clear)
        A.boarding_metric_install()
        self.hale = lifeform_spawn("Dr Ines Hale", "", "boarding,medical")
        self.reyes = lifeform_spawn("Lt Sam Reyes", "", "boarding,weapons")
        A.boarding_assign(HALE, self.hale)
        A.boarding_assign(REYES, self.reyes)
        # HER side scene, the terminal - Reyes is elsewhere.
        A.boarding_encounter(_scenes(), "terminal", HALE, channel="terminal")

    def area(self, client_id):
        ta = TextArea("ta%d" % client_id, "")
        ta.bounds = Bounds(0, 0, 100, 100)
        A.boarding_reader(ta, client_id)
        ta.calc_rich(client_id)
        return ta

    def buttons(self, ta, client_id):
        ta.calc_rich(client_id)
        return sorted(c["display"] for c in ta._choice_map.values())

    def press_signal(self, client_id, index):
        A._boarding_reader_on_pick(A.BOARDING_PICK_SIGNAL, {
            "SIGNAL_CLIENT_ID": client_id, "i": str(index),
            "seq": str(A.boarding_seq_for(client_id)),
            "SIGNAL_CHOICE": "Send the sentry its recognition update"})

    def test_fixture_she_can_choose_while_standing(self):
        self.assertEqual(2, len(A.boarding_choices(HALE)))
        self.assertEqual(["Send the sentry its recognition update", "Step back"],
                         self.buttons(self.area(HALE), HALE))

    def test_a_downed_member_is_offered_nothing(self):
        K.boarding_hurt(self.hale, 99)
        self.assertTrue(K.boarding_is_down(self.hale), "fixture: she is not down")
        self.assertEqual([], A.boarding_choices(HALE))
        self.assertEqual([], A.boarding_choices_for(HALE, self.hale))

    def test_a_press_from_a_button_drawn_before_she_fell_does_nothing(self):
        """The engine case: the scene was open, she fell, she kept pressing."""
        seq = A.boarding_seq_for(HALE)
        K.boarding_hurt(self.hale, 99)
        self.assertFalse(A.boarding_answer(HALE, 0, seq=seq),
                         "a downed member's press was accepted")
        self.assertEqual("terminal", A.boarding_scene("terminal"),
                         "the outcome applied: the scene moved on")
        self.assertEqual(seq, A.boarding_seq_for(HALE), "the token moved for a refused press")

    def test_the_transcript_press_is_refused_and_not_written_down_as_made(self):
        ta = self.area(HALE)
        self.assertTrue(self.buttons(ta, HALE), "fixture: no buttons before she fell")
        K.boarding_hurt(self.hale, 99)
        self.press_signal(HALE, 0)
        self.assertEqual("terminal", A.boarding_scene("terminal"))
        text = A.boarding_reader_text(HALE)
        self.assertNotIn("chosen://", text, "her refused press was written down as taken")
        self.assertNotIn("The sentry stops", text)

    def test_her_open_scene_says_she_is_down_in_place_of_her_choices(self):
        ta = self.area(HALE)
        self.assertTrue(self.buttons(ta, HALE))
        K.boarding_hurt(self.hale, 99)
        ta = self.area(HALE)                       # the Act app repaints
        self.assertEqual([], self.buttons(ta, HALE), "her old buttons are still live")
        text = A.boarding_reader_text(HALE)
        self.assertIn("Dr Ines Hale is DOWN - needs a medkit.", text)
        self.assertIn("DOOR SEALED", text, "the scene itself is still shown")
        self.assertEqual(1, text.count("is DOWN"), "said once")

    def test_back_on_her_feet_her_choices_come_back(self):
        self.area(HALE)
        K.boarding_hurt(self.hale, 99)
        self.area(HALE)
        K.boarding_revive(self.hale)
        ta = self.area(HALE)
        self.assertEqual(["Send the sentry its recognition update", "Step back"],
                         self.buttons(ta, HALE))
        self.assertTrue(A.boarding_answer(HALE, 0, seq=A.boarding_seq_for(HALE)))
        self.assertEqual("update", A.boarding_scene("terminal"))

    def test_the_act_list_says_she_is_down(self):
        K.boarding_hurt(self.hale, 99)
        self.assertTrue(A.boarding_console_down(HALE))
        self.assertFalse(A.boarding_console_down(REYES))


if __name__ == "__main__":
    unittest.main()
