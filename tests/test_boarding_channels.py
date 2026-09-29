"""Several conversations at once - one scene per CHANNEL.

A party spread across an open world is not in one conversation. The medic is talking to a
survivor in the caves while the engineer argues with a deputy in the colony, and each of
them must read and answer only their own. The properties under test:

* **Nothing changes for a mission that never opens a channel.** Every console is in the
  party channel and every function defaults to it.
* **Two channels answer in the same frame without touching each other.**
* **A button from one channel can never answer another** - the seq is global.
* **A guard word that is not a job is not forwarded** - LandingParty's `briefed` ending
  was handed to the duty console before anybody had been briefed.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.signal import signal_emit

MED, ENG, SEC = 7, 8, 9


def _scene(key, body):
    return {"key": key, "display_text": key, "description": body,
            "data": {"speaker": "x"}}


SCENES = {
    "party": _scene("party", "% Everyone is here.\n- [Go on](party2)\n"),
    "party2": _scene("party2", "% Still here.\n- [Stop]()\n"),
    "survivor": _scene("survivor", "% She is cold.\n"
                                   "- [Treat her](survivor2) if medical >= 1\n"
                                   "- [Leave]()\n"),
    "survivor2": _scene("survivor2", "% She breathes.\n- [Done]()\n"),
    "deputy": _scene("deputy", "% He will not look at you.\n"
                               "- [Press him](deputy2)\n- [Walk away]()\n"),
    "deputy2": _scene("deputy2", "% He talks.\n- [Enough]()\n"),
    "gate": _scene("gate", "% The shutter.\n"
                           "- [Open it](party) if briefed >= 1\n"
                           "- [Treat her](party) if medical >= 1\n"
                           "- [Wait]()\n"),
}


class ChannelBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        A.boarding_clear()
        A.boarding_forwarding(False)
        self.addCleanup(A.boarding_clear)
        self.addCleanup(A.boarding_forwarding, False)
        A.boarding_metric_install()
        self.bodies = {}
        for cid, name, roles in ((MED, "Sato", "boarding, medical"),
                                 (ENG, "Kovac", "boarding, engineering"),
                                 (SEC, "Lund", "boarding, security")):
            GuiClient(cid)
            body = lifeform_spawn(name, "", roles)
            set_inventory_value(body.id, A.JOBS_KEY, [roles.split(", ")[1]])
            A.boarding_assign(cid, body.id)
            self.bodies[cid] = body.id

    def tearDown(self):
        FrameContext.context = None

    def labels(self, cid):
        return [c.label for c in A.boarding_choices(cid)]


class TestTheDefaultIsTheParty(ChannelBase):
    def test_every_console_starts_in_the_party(self):
        for cid in (MED, ENG, SEC):
            self.assertEqual(A.boarding_channel_of(cid), A.boarding_party_channel())

    def test_a_party_scene_reaches_everyone(self):
        A.boarding_scene_begin(SCENES, "party")
        for cid in (MED, ENG, SEC):
            self.assertEqual(self.labels(cid), ["Go on"])

    def test_seq_for_a_party_console_is_the_party_seq(self):
        A.boarding_scene_begin(SCENES, "party")
        self.assertEqual(A.boarding_seq_for(MED), A.boarding_seq())


class TestTwoConversationsAtOnce(ChannelBase):
    def setUp(self):
        super().setUp()
        A.boarding_scene_begin(SCENES, "party")
        self.cave = A.boarding_encounter(SCENES, "survivor", MED)
        self.colony = A.boarding_encounter(SCENES, "deputy", ENG)

    def test_each_console_sees_its_own_scene(self):
        self.assertEqual(self.labels(MED), ["Treat her", "Leave"])
        self.assertEqual(self.labels(ENG), ["Press him", "Walk away"])
        self.assertEqual(self.labels(SEC), ["Go on"])

    def test_three_scenes_are_open(self):
        self.assertEqual(A.boarding_scene_count(), 3)
        self.assertEqual(set(A.boarding_channels()),
                         {A.boarding_party_channel(), self.cave, self.colony})

    def test_both_answer_in_the_same_frame(self):
        med_seq, eng_seq = A.boarding_seq_for(MED), A.boarding_seq_for(ENG)
        self.assertTrue(A.boarding_answer(MED, 0, seq=med_seq))
        self.assertTrue(A.boarding_answer(ENG, 0, seq=eng_seq))
        self.assertEqual(A.boarding_scene(self.cave), "survivor2")
        self.assertEqual(A.boarding_scene(self.colony), "deputy2")
        self.assertEqual(A.boarding_scene(), "party")

    def test_A_SEQ_FROM_ANOTHER_CHANNEL_IS_REFUSED(self):
        """Seqs are unique across channels, so a leftover button answers nothing."""
        self.assertFalse(A.boarding_answer(MED, 0, seq=A.boarding_seq_for(ENG)))
        self.assertEqual(A.boarding_scene(self.cave), "survivor")

    def test_seqs_never_collide(self):
        seqs = {A.boarding_seq_for(c) for c in (MED, ENG, SEC)}
        self.assertEqual(len(seqs), 3)

    def test_ending_a_side_scene_sends_its_members_back(self):
        got = []
        from sbs_utils.procedural.signal import signal_observe, signal_unobserve

        def obs(name, data):
            if name == "boarding_scene_ended":
                got.append(data)
        signal_observe(obs)
        self.addCleanup(signal_unobserve, obs)
        A.boarding_answer(ENG, 1, seq=A.boarding_seq_for(ENG))       # Walk away
        self.assertEqual(A.boarding_channel_of(ENG), A.boarding_party_channel())
        self.assertEqual(self.labels(ENG), ["Go on"])
        self.assertFalse(A.boarding_is_open(self.colony))
        self.assertEqual(got[-1]["BOARDING_CHANNEL"], self.colony)
        self.assertEqual(got[-1]["BOARDING_CLIENTS"], [ENG])

    def test_a_party_answer_does_not_move_a_side_scene(self):
        A.boarding_answer(SEC, 0, seq=A.boarding_seq_for(SEC))
        self.assertEqual(A.boarding_scene(), "party2")
        self.assertEqual(A.boarding_scene(self.cave), "survivor")

    def test_walking_up_to_an_open_conversation_joins_it(self):
        ch = A.boarding_encounter(SCENES, "deputy", SEC)
        self.assertEqual(ch, self.colony)
        self.assertEqual(self.labels(SEC), ["Press him", "Walk away"])
        self.assertEqual(A.boarding_channel_members(self.colony), {ENG, SEC})

    def test_a_sticky_channel_keeps_its_members(self):
        A.boarding_channel_open(self.colony, sticky=True)
        A.boarding_answer(ENG, 1, seq=A.boarding_seq_for(ENG))
        self.assertEqual(A.boarding_channel_of(ENG), self.colony)

    def test_an_encounter_with_no_scene_opens_nothing(self):
        self.assertIsNone(A.boarding_encounter(SCENES, "nobody", SEC))
        self.assertEqual(A.boarding_channel_of(SEC), A.boarding_party_channel())

    def test_the_reset_empties_every_channel(self):
        A.boarding_clear()
        self.assertEqual(A.boarding_scene_count(), 0)
        self.assertEqual(A.boarding_channel_of(MED), A.boarding_party_channel())


class TestTheReaderFollowsTheChannel(ChannelBase):
    def setUp(self):
        super().setUp()
        A.boarding_scene_begin(SCENES, "party")

    def test_a_reader_shows_its_own_channel(self):
        A.boarding_encounter(SCENES, "survivor", MED)
        self.assertIn("She is cold.", A.boarding_reader_text(MED))
        self.assertNotIn("She is cold.", A.boarding_reader_text(SEC))

    def test_a_change_of_channel_is_marked(self):
        A.boarding_reader_text(MED)
        A.boarding_encounter(SCENES, "survivor", MED)
        text = A.boarding_reader_text(MED)
        self.assertIn("~ ~ ~", text)
        self.assertNotIn("---", text)        # a text area drew that as "- ---"
        self.assertLess(text.index("Everyone is here."), text.index("She is cold."))

    def test_A_PICK_IN_ONE_CHANNEL_LEAVES_ANOTHERS_CHOICES_LIVE(self):
        A.boarding_encounter(SCENES, "survivor", MED)
        A.boarding_reader_text(MED)
        A.boarding_reader_text(SEC)
        signal_emit(A.BOARDING_PICK_SIGNAL, {"SIGNAL_CLIENT_ID": MED, "i": "0",
                                             "seq": str(A.boarding_seq_for(MED)),
                                             "SIGNAL_CHOICE": "Treat her"})
        self.assertEqual(A.boarding_scene(A.boarding_channel_of(MED)), "survivor2")
        self.assertIn("signal://boarding_pick", A.boarding_reader_text(SEC))


class TestAReaderInARegionIsRepaintedByItsOwner(ChannelBase):
    """Engine-seen: a pick wrote the Act app's text area OUT OF BAND after the pick had
    ended the conversation - the xESS had already rebuilt the region as "Nothing to
    decide here", and the stale area painted the transcript over it."""

    class _Area:
        def __init__(self):
            self.writes = 0
            self._v = ""

        @property
        def value(self):
            return self._v

        @value.setter
        def value(self, v):
            self.writes += 1
            self._v = v

    def test_a_pick_moves_the_revision_and_never_touches_the_area(self):
        area = self._Area()
        A.boarding_encounter(SCENES, "deputy", ENG)
        A.boarding_reader(area, ENG, in_region=True)
        before_writes, before_rev = area.writes, A.boarding_reader_revision(ENG)
        signal_emit(A.BOARDING_PICK_SIGNAL, {"SIGNAL_CLIENT_ID": ENG, "i": "1",
                                             "seq": str(A.boarding_seq_for(ENG)),
                                             "SIGNAL_CHOICE": "Walk away"})
        self.assertEqual(area.writes, before_writes)
        self.assertGreater(A.boarding_reader_revision(ENG), before_rev)
        self.assertIn("The conversation is over.", A.boarding_reader_text(ENG))

    def test_a_top_level_reader_is_still_written_directly(self):
        area = self._Area()
        A.boarding_encounter(SCENES, "deputy", ENG)
        A.boarding_reader(area, ENG, in_region=False)
        before = area.writes
        signal_emit(A.BOARDING_PICK_SIGNAL, {"SIGNAL_CLIENT_ID": ENG, "i": "0",
                                             "seq": str(A.boarding_seq_for(ENG)),
                                             "SIGNAL_CHOICE": "Press him"})
        self.assertGreater(area.writes, before)

    def test_the_transcript_outlives_the_conversation(self):
        A.boarding_encounter(SCENES, "deputy", ENG)
        A.boarding_reader_text(ENG)
        A.boarding_answer(ENG, 1, seq=A.boarding_seq_for(ENG))
        self.assertTrue(A.boarding_reader_has_text(ENG))


class TestOnlyJobsAreForwarded(ChannelBase):
    def setUp(self):
        super().setUp()
        A.boarding_forwarding(True)
        A.boarding_assign(MED, None)                  # nobody is a medic now
        A.boarding_scene_begin(SCENES, "gate")

    def forwarded(self):
        return [c.label for c in A.boarding_orphan_choices()]

    def test_a_missing_job_is_forwarded(self):
        self.assertIn("Treat her", self.forwarded())

    def test_A_PROGRESS_ROLE_IS_NOT_A_JOB(self):
        """`briefed` was forwarded before anybody was briefed, handing over the ending."""
        self.assertNotIn("Open it", self.forwarded())
        self.assertNotIn("Open it", self.labels(A.boarding_duty_client()))

    def test_a_registered_word_is_a_job(self):
        A.boarding_register_jobs("briefed")
        self.assertIn("Open it", self.forwarded())

    def test_a_cast_word_is_a_job(self):
        """What a body was CAST with is a job even when it is not a stock one."""
        geo = lifeform_spawn("Ito", "", "boarding, geology")
        set_inventory_value(geo.id, A.JOBS_KEY, ["geology"])
        self.assertIn("geology", A.boarding_job_vocabulary())
        self.assertNotIn("briefed", A.boarding_job_vocabulary())


class TestForwardingIsPerChannel(ChannelBase):
    def test_the_medic_in_the_party_does_not_cover_a_cave_with_no_medic(self):
        """Forwarding asks who is HERE: a medic in the colony cannot treat a survivor
        in the caves, so the cave's duty console catches it."""
        A.boarding_forwarding(True)
        ch = A.boarding_encounter(SCENES, "survivor", ENG, members=[SEC])
        self.assertEqual(A.boarding_duty_client(ch), ENG)
        self.assertIn("Treat her", [c.label for c in A.boarding_orphan_choices(ch)])
        self.assertIn("Treat her", self.labels(ENG))
        self.assertNotIn("Treat her", self.labels(SEC))


if __name__ == "__main__":
    unittest.main()
