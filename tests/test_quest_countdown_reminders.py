"""Deadline reminders on comms: escalating, latched, and never from nobody (PRM-11).

A countdown that only lives on a tab is one the crew discovers by failing. These are the
reminders. The whole design question was "how is this not spam", so that is what most of
these assert: absolute marks that FIT under the deadline, each fired exactly once, and a
single tick crossing several marks producing ONE message rather than three.

    python -m unittest tests.test_quest_countdown_reminders
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.quest import quest_add, QuestState
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.timers import set_timer


class CountdownReminderTests(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        QD.quest_dispatch_voice_clear()
        self.agent = Agent()
        self.agent.id = get_story_id()
        self.agent.add()
        self.sent = []
        self._real = QD._quest_countdown_send
        QD._quest_countdown_send = lambda aid, qid, data, mark, left: self.sent.append(mark)

    def tearDown(self):
        QD._quest_countdown_send = self._real
        QD.quest_dispatch_voice_clear()

    def _job(self, minutes=6, key="mercy"):
        quest_add(self.agent.id, key, "Mercy Run", "d", state=QuestState.ACTIVE,
                  data={"fail_after": {"minutes": minutes}})

    def _at(self, seconds_left, total_minutes=6, key="mercy"):
        """Put the deadline timer at `seconds_left` and run one watcher tick."""
        set_timer(self.agent.id, "qfail:" + key, seconds=seconds_left)
        QD.quest_tick_countdown_reminders()

    def test_marks_fire_in_order_as_the_clock_closes(self):
        self._job()
        for left in (400, 290, 115, 55, 25):
            self._at(left)
        self.assertEqual([300, 120, 60, 30], self.sent)

    def test_each_mark_fires_exactly_once(self):
        self._job()
        for _ in range(5):
            self._at(100)          # five ticks, all past the 120 mark
        self.assertEqual([120], self.sent)

    def test_crossing_several_marks_at_once_sends_ONE_message(self):
        """A long frame or a restart must not produce a burst - the most urgent wins and
        the rest latch silently."""
        self._job()
        self._at(50)               # 300, 120 and 60 all qualify in one tick
        self.assertEqual([60], self.sent)
        self._at(25)
        self.assertEqual([60, 30], self.sent, "the 30 mark is still live afterwards")

    def test_a_short_deadline_gets_only_the_marks_that_fit(self):
        """45 seconds must not open with 'five minutes remaining'."""
        self._job(minutes=0, key="short")
        quest_add(self.agent.id, "short45", "Short", "d", state=QuestState.ACTIVE,
                  data={"fail_after": {"seconds": 45}})
        set_timer(self.agent.id, "qfail:short45", seconds=40)
        QD.quest_tick_countdown_reminders()
        set_timer(self.agent.id, "qfail:short45", seconds=20)
        QD.quest_tick_countdown_reminders()
        self.assertEqual([30], self.sent)

    def test_a_mark_equal_to_the_deadline_never_fires(self):
        """A 5-minute job must not announce '5:00 remaining' the instant it is accepted."""
        quest_add(self.agent.id, "five", "Five", "d", state=QuestState.ACTIVE,
                  data={"fail_after": {"minutes": 5}})
        set_timer(self.agent.id, "qfail:five", seconds=299)
        QD.quest_tick_countdown_reminders()
        self.assertEqual([], self.sent)

    def test_a_quest_with_no_deadline_is_untouched(self):
        quest_add(self.agent.id, "untimed", "Untimed", "d", state=QuestState.ACTIVE)
        QD.quest_tick_countdown_reminders()
        self.assertEqual([], self.sent)


class SpeakerTests(unittest.TestCase):
    """Who talks - authored first, then the holder, then dispatch, then silence."""

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        QD.quest_dispatch_voice_clear()

    def tearDown(self):
        QD.quest_dispatch_voice_clear()

    def test_no_voice_anywhere_means_silence(self):
        """A reminder from nobody is worse than no reminder."""
        self.assertIsNone(QD._quest_speaker("q", {}))

    def test_the_registered_dispatch_voice_is_the_fallback(self):
        QD.quest_dispatch_voice(12345)
        self.assertEqual(12345, QD._quest_speaker("q", {}))

    def test_a_name_is_resolved_LAZILY(self):
        """Missions register their voice while setting the story up - before the cast has
        spawned - so resolving at registration would store None for the whole mission."""
        QD.quest_dispatch_voice("admiral")
        self.assertEqual("admiral", QD.quest_dispatch_voice(), "stored raw, not resolved")

    def test_the_reset_forgets_it(self):
        QD.quest_dispatch_voice(999)
        QD.quest_dispatch_voice_clear()
        self.assertIsNone(QD.quest_dispatch_voice())


if __name__ == "__main__":
    unittest.main()


class CastKeyResolutionTests(unittest.TestCase):
    """`Speaker: admiral` must find the CAST character of that name.

    A cast lifeform carries `amd_lifeform:<key>` - not a landmark role, and not its own
    key as a plain role. So naming one (the obvious thing to write) resolved to nothing,
    silently: a quest's voice fell through to a fallback never meant to speak for it, and
    an Action direction ran against an empty actor set. Nothing logged; nothing happened.
    """

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def test_a_cast_character_resolves_by_its_record_key(self):
        from sbs_utils.procedural.amd_lifeforms import lifeform_from_record
        from sbs_utils.procedural.amd_action import amd_action_actors
        from sbs_utils.mast.mast_node import MastDataObject
        agent = lifeform_from_record(MastDataObject(
            {"key": "admiral", "name": "Admiral Harkin", "face": "terran_male",
             "roles": "fb_brass"}))
        self.assertIn(agent.id, amd_action_actors("admiral"))

    def test_an_unknown_name_still_resolves_to_nothing(self):
        from sbs_utils.procedural.amd_action import amd_action_actors
        self.assertEqual(set(), amd_action_actors("nobody_by_that_name"))


class ReminderWordingTests(unittest.TestCase):
    """What the reminder actually SAYS - authored line, else a voice-appropriate default."""

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.machine = 4242                       # no face registered -> a transmitter

    def _person(self):
        from sbs_utils.faces import set_face
        set_face(777, "ter #fff 4 4;")
        return 777

    def test_an_authored_line_wins_and_carries_the_clock(self):
        body = QD._quest_countdown_body(
            {"reminder": "LIFE SUPPORT {time} FROM FAILURE."}, self.machine, "1:00", False)
        self.assertEqual("LIFE SUPPORT 1:00 FROM FAILURE.", body)

    def test_an_authored_line_without_the_token_is_sent_as_written(self):
        body = QD._quest_countdown_body({"reminder": "HULL BREACH IMMINENT"},
                                        self.machine, "0:30", True)
        self.assertEqual("HULL BREACH IMMINENT", body)

    def test_a_faceless_speaker_transmits(self):
        """A beacon, a ship's transmitter, a hull with the distress signal still running."""
        body = QD._quest_countdown_body({}, self.machine, "2:00", False)
        self.assertIn("AUTOMATED SIGNAL", body)
        self.assertIn("2:00", body)

    def test_a_cast_character_speaks(self):
        body = QD._quest_countdown_body({}, self._person(), "2:00", False)
        self.assertNotIn("AUTOMATED", body)
        self.assertEqual("2:00 remaining.", body)

    def test_the_final_mark_says_so_in_both_voices(self):
        self.assertIn("FINAL", QD._quest_countdown_body({}, self.machine, "0:30", True))
        self.assertIn("Final", QD._quest_countdown_body({}, self._person(), "0:30", True))
