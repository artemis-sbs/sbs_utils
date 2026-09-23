"""The boarding scene read as a transcript: `boarding_reader` in a gui_text_area.

Each beat's line and this console's choices land in a text area as `signal://`
lines; a pick goes through the SAME `boarding_answer` arbitration the button screen
uses, and every console reading the scene gets the next beat added below.

Run: python -m unittest tests.test_boarding_reader
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural.amd import amd_choices_settle
from sbs_utils.pages.layout.text_area import TextArea
from sbs_utils.pages.layout.bounds import Bounds


SCENE_BODY = (
    "% The body is cold.\n"
    "- [Examine the body](autopsy) if medical >= 1\n"
    "- [Force the panel](panel_open) if engineering >= 1\n"
    "- [Back out](corridor)\n"
)


def _scenes():
    def node(key, body):
        return {"key": key, "display_text": key, "description": body,
                "data": {"speaker": "outpost"}}
    return {
        "lab": node("lab", SCENE_BODY),
        "autopsy": node("autopsy", "% Phaser burn, close range.\n- [Report it](corridor)\n"),
        "panel_open": node("panel_open", "% The relay is fused.\n- [Report it](corridor)\n"),
        "corridor": node("corridor", "% You regroup.\n"),
    }


class ReaderTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        self._prev_metric = D._METRIC_RESOLVER
        A.boarding_clear()
        A.boarding_metric_install()
        self.doc = lifeform_spawn("Dr Sorel", "terran_female", "boarding,medical")
        self.eng = lifeform_spawn("Chief Ruiz", "terran_male", "boarding,engineering")
        A.boarding_assign(101, self.doc)
        A.boarding_assign(102, self.eng)
        A.boarding_scene_begin(_scenes(), "lab", speaker="outpost")

    def tearDown(self):
        A.boarding_clear()
        D.dialogue_set_metric_resolver(self._prev_metric)
        FrameContext.context = None

    def area(self, client_id):
        ta = TextArea(f"ta{client_id}", "")
        ta.bounds = Bounds(0, 0, 100, 100)
        A.boarding_reader(ta, client_id)
        ta.calc_rich(client_id)
        return ta

    def press(self, ta, client_id, words):
        ta.calc_rich(client_id)
        tag = next(t for t, c in ta._choice_map.items() if c["display"] == words)
        return ta.choose(tag, client_id)

    def test_each_console_reads_its_own_choices(self):
        doc = self.area(101)
        eng = self.area(102)
        self.assertEqual(sorted(c["display"] for c in doc._choice_map.values()),
                         ["Back out", "Examine the body"])
        self.assertEqual(sorted(c["display"] for c in eng._choice_map.values()),
                         ["Back out", "Force the panel"])
        self.assertIn("The body is cold.", doc.content)

    def test_a_pick_answers_the_beat_and_continues_every_transcript(self):
        doc = self.area(101)
        eng = self.area(102)
        self.press(doc, 101, "Examine the body")
        self.assertEqual(A.boarding_scene(), "autopsy")

        doc_text = "\n".join(doc.content)
        self.assertIn("[Examine the body](chosen://boarding_pick)", doc_text)
        self.assertNotIn("Back out", doc_text)
        self.assertTrue(doc_text.index("Examine the body") < doc_text.index("Phaser burn"))

        # The engineer's screen moved on too: their unused choices are gone, the next
        # beat is there, and so are their new choices.
        eng_text = "\n".join(eng.content)
        self.assertNotIn("Force the panel", eng_text)
        self.assertIn("Phaser burn, close range.", eng_text)
        eng.calc_rich(102)
        self.assertEqual([c["display"] for c in eng._choice_map.values()], ["Report it"])

    def test_the_transcript_survives_a_rebuild(self):
        doc = self.area(101)
        self.press(doc, 101, "Examine the body")
        again = self.area(101)          # the screen repainted: a brand new widget
        self.assertEqual(again.content, doc.content)

    def test_another_consoles_pick_moves_this_one_on(self):
        doc = self.area(101)
        eng = self.area(102)
        self.press(eng, 102, "Force the panel")
        self.assertEqual(A.boarding_scene(), "panel_open")
        self.assertIn("The relay is fused.", "\n".join(doc.content))

    def test_a_stale_press_is_refused(self):
        doc = self.area(101)
        eng = self.area(102)
        doc.calc_rich(101)
        held = next(t for t, c in doc._choice_map.items() if c["display"] == "Back out")
        stale = dict(doc._choice_map[held])
        self.press(eng, 102, "Force the panel")
        # The doctor still holds a button rendered before the beat moved: its seq is
        # old, so boarding_answer refuses it and the scene stays where it is.
        doc._choice_map[held] = stale
        doc.choose(held, 101)
        self.assertEqual(A.boarding_scene(), "panel_open")

    def test_the_end_of_the_scene_is_said(self):
        doc = self.area(101)
        self.press(doc, 101, "Examine the body")
        self.press(doc, 101, "Report it")
        self.assertIn("You regroup.", "\n".join(doc.content))


class RegionTests(ReaderTests.__bases__[0]):
    """In a region the area must NOT draw itself (the engine overdraws); the owner
    rebuilds off boarding_reader_revision, and the rebuilt area keeps the scroll."""

    setUp = ReaderTests.setUp
    tearDown = ReaderTests.tearDown

    def region_area(self, client_id):
        ta = TextArea(f"ta{client_id}", "")
        ta.bounds = Bounds(0, 0, 100, 100)
        A.boarding_reader(ta, client_id, in_region=True)
        ta.calc_rich(client_id)
        return ta

    def test_a_scroll_asks_the_owner_and_draws_nothing(self):
        ta = self.region_area(101)
        drawn = []
        ta.present = lambda event: drawn.append(event)
        before = A.boarding_reader_revision(101)
        ta.scroll_line = 3
        ta._repaint(FakeEvent(client_id=101))
        self.assertEqual(drawn, [])
        self.assertGreater(A.boarding_reader_revision(101), before)

    def test_the_rebuilt_area_keeps_the_scroll(self):
        ta = self.region_area(101)
        ta.scroll_line, ta.follow_tail = 2, False
        ta._repaint(FakeEvent(client_id=101))
        again = TextArea("ta101b", "")
        again.bounds = Bounds(0, 0, 100, 100)
        A.boarding_reader(again, 101, in_region=True)
        self.assertEqual(again.restore_scroll, (2, False))

    def test_a_pick_scrolls_to_the_bottom_and_a_scroll_up_holds(self):
        loop = {"a": {"key": "a", "display_text": "a", "data": {"speaker": "x"},
                      "description": "% A long line about the corridor and the cold.\n"
                                     "- [Again](a)\n- [Other](a)\n"}}
        A.boarding_scene_begin(loop, "a", speaker="x")

        def build():
            ta = TextArea("ta", "")
            ta.bounds = Bounds(0, 0, 100, 15)       # short, so the transcript scrolls
            A.boarding_reader(ta, 101, in_region=True)
            ta.calc_rich(101)
            return ta

        def pick(ta):
            tag = next(k for k, c in ta._choice_map.items() if c["display"] == "Again")
            ta.on_message(FakeEvent(client_id=101, sub_tag=tag))
            return build()                            # the region owner's rebuild

        def shows_the_end(ta):
            # What _present draws: from `last_line - scroll_line` down until a line would
            # overflow. The end is on screen when the LAST line makes it in. (This test
            # used to compare scroll_line with the "tail" value - which is the TOP; the
            # engine showed it.)
            first = max(0, ta.last_line - ta.scroll_line)
            y = 0
            for i in range(first, len(ta.lines)):
                y += ta.lines[i].height
                if y > ta.bounds.height:
                    return False
            return True

        ta = build()
        for _ in range(8):
            ta = pick(ta)
        self.assertTrue(ta.need_v_scroll)
        self.assertTrue(shows_the_end(ta))

        ta.scroll_line, ta.follow_tail = 1, False     # the reader scrolls back to read
        ta._repaint(FakeEvent(client_id=101))
        ta = build()
        self.assertEqual(ta.scroll_line, 1)           # held, not yanked down
        self.assertFalse(shows_the_end(ta))

        ta = pick(ta)
        self.assertTrue(shows_the_end(ta))            # a pick goes to the new beat

    def test_a_pick_in_a_region_still_answers(self):
        ta = self.region_area(101)
        ta.present = lambda event: self.fail("drew itself inside a region")
        tag = next(t for t, c in ta._choice_map.items() if c["display"] == "Examine the body")
        ta.on_message(FakeEvent(client_id=101, sub_tag=tag))
        self.assertEqual(A.boarding_scene(), "autopsy")


class SettleTests(unittest.TestCase):
    TEXT = "Hi.\n[A](signal://s?i=0)\n[B](signal://s?i=1)\n\nLater.\n[C](signal://t)"

    def test_the_chosen_one_stays_and_its_siblings_go(self):
        out = amd_choices_settle(self.TEXT, "B")
        self.assertIn("[B](chosen://s)", out)
        self.assertNotIn("[A]", out)
        self.assertNotIn("[C]", out)

    def test_with_no_choice_every_group_goes(self):
        out = amd_choices_settle(self.TEXT)
        self.assertNotIn("signal://", out)
        self.assertIn("Later.", out)


if __name__ == "__main__":
    unittest.main()
