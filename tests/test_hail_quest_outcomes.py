"""Answering a hail resolves a quest - `- [Take the case]() ; completes florbin/brief`.

The other half of `Action: X hails Y`. Before this, a choice could only emit a raw
signal, so a mission wanting "answering the call opens the case" wrote a
`//shared/signal/hail` route with three guards to translate the answer into a quest
signal. Every mission would have rewritten that.

These outcomes run inside `hail_answer`, which is server-side and seq-arbitrated, so
they fire exactly once however many consoles are connected - the property the
hand-rolled bridge had to be careful about and this gets for free.

    python -m unittest tests.test_hail_quest_outcomes
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent, get_story_id, clear_shared
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import hail as H
from sbs_utils.procedural.links import link
from sbs_utils.procedural.quest import QuestState, quest_add, quest_get_state
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.spawn import player_spawn

C_COMMS = 0x8000000000000001
NL = "\n"


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


def _scene(outcome):
    return {"brief": {
        "key": "brief",
        "data": {"speaker": "ds1", "when": "hail"},
        "description": ("The ambassador was taken." + NL
                        + f"- [Take the case]() ; {outcome}" + NL),
    }}


class OutcomeBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        Agent.clear()
        clear_shared()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        H.hail_reset()
        D.dialogue_scenes_registry_clear()
        self.shared = Agent()
        self.shared.id = get_story_id()
        self.shared.add()
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        console = Agent()
        console.id = C_COMMS
        console.add()
        for r in ("console", "comms"):
            add_role(C_COMMS, r)
        link(self.ship, "consoles", C_COMMS)

    def tearDown(self):
        FrameContext.context = None
        H.hail_reset()
        D.dialogue_scenes_registry_clear()

    def answer(self, outcome, state=QuestState.IDLE, agent=None, quest_id="brief_q"):
        quest_add(self.shared.id if agent is None else agent, quest_id,
                  "Take the case", "d", state=state)
        scenes = _scene(outcome)
        D.dialogue_register_scenes(scenes)
        H.hail_offer(self.ship, scene="brief", speaker="ds1")
        H.hail_accept(self.ship)
        while H.hail_advance(self.ship):
            pass
        return H.hail_answer(self.ship, 0, C_COMMS)


class TheVerbs(OutcomeBase):
    def test_accepts_activates(self):
        self.assertTrue(self.answer("accepts brief_q"))
        self.assertEqual(quest_get_state(self.shared.id, "brief_q"), QuestState.ACTIVE)

    def test_completes_completes(self):
        self.assertTrue(self.answer("completes brief_q", state=QuestState.ACTIVE))
        self.assertEqual(quest_get_state(self.shared.id, "brief_q"), QuestState.COMPLETE)

    def test_fails_fails(self):
        self.assertTrue(self.answer("fails brief_q", state=QuestState.ACTIVE))
        self.assertEqual(quest_get_state(self.shared.id, "brief_q"), QuestState.FAILED)

    def test_a_nested_arc_step_resolves_by_its_path(self):
        quest_add(self.shared.id, "florbin", "Florbin", "d", state=QuestState.ACTIVE)
        quest_add(self.shared.id, "florbin/brief", "Brief", "d", state=QuestState.ACTIVE)
        D.dialogue_register_scenes(_scene("completes florbin/brief"))
        H.hail_offer(self.ship, scene="brief", speaker="ds1")
        H.hail_accept(self.ship)
        while H.hail_advance(self.ship):
            pass
        H.hail_answer(self.ship, 0, C_COMMS)
        self.assertEqual(quest_get_state(self.shared.id, "florbin/brief"),
                         QuestState.COMPLETE)


class WhoseQuest(OutcomeBase):
    """A hail belongs to one SHIP; a `Scope: shared` quest lives on the story agent."""

    def test_a_shared_quest_is_found_from_a_ships_hail(self):
        self.answer("completes brief_q", state=QuestState.ACTIVE)
        self.assertEqual(quest_get_state(self.shared.id, "brief_q"), QuestState.COMPLETE)

    def test_the_answering_ships_own_copy_wins(self):
        # Two bridges each carrying their own copy of a job resolve their own - one
        # crew answering must not close the other crew's job.
        other = to_id(player_spawn(0, 0, 900, "Hera", "tsn", "battle"))
        quest_add(other, "job", "Job", "d", state=QuestState.ACTIVE)
        self.answer("completes job", state=QuestState.ACTIVE, agent=self.ship,
                    quest_id="job")
        self.assertEqual(quest_get_state(self.ship, "job"), QuestState.COMPLETE)
        self.assertEqual(quest_get_state(other, "job"), QuestState.ACTIVE)


class ItNeverRefusesThePick(OutcomeBase):
    """Returning False from an outcome refuses the whole choice.

    A quest id that does not resolve must therefore NOT return False: the button
    would go dead and the player would be stuck in a conversation with no way out -
    the worst possible reading of a typo. It logs and lets the answer through.
    """

    def test_an_unknown_quest_still_lets_the_answer_land(self):
        self.assertTrue(self.answer("completes no_such_quest"))
        self.assertFalse(H.hail_is_active(self.ship))

    def test_a_verb_with_no_quest_after_it_still_answers(self):
        self.assertTrue(self.answer("completes"))
        self.assertFalse(H.hail_is_active(self.ship))

    def test_a_MISSION_verb_can_still_refuse(self):
        # OU's `costs` means "you cannot afford this", and that must keep working.
        D.dialogue_register_outcome("costs", lambda a, s, t: False)
        try:
            self.assertFalse(self.answer("costs 200 credits"))
            self.assertTrue(H.hail_is_active(self.ship))
        finally:
            D._OUTCOME_HANDLERS.pop("costs", None)


class TheSignalOutcomeIsAMilestone(OutcomeBase):
    """`; signal X` emitted only the RAW signal, so it could not drive a quest's
    `Done when: signal X` - which is what the two lines plainly read as."""

    def _answer_and_capture(self):
        seen = []
        real = D.signal_emit
        D.signal_emit = lambda name, data=None: seen.append((name, data or {}))
        try:
            self.answer("signal case_opened", state=QuestState.ACTIVE)
        finally:
            D.signal_emit = real
        return seen

    def test_it_emits_the_quest_milestone(self):
        names = [d.get("SIGNAL_NAME") for n, d in self._answer_and_capture()
                 if n == "quest_signal"]
        self.assertIn("case_opened", names)

    def test_the_raw_signal_still_goes_out(self):
        self.assertIn("case_opened", [n for n, _ in self._answer_and_capture()])


if __name__ == "__main__":
    unittest.main()
