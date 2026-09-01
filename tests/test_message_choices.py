"""A message that asks a question, and the away team's live audiences.

The architecture is `hail.py`'s, and so is the property that matters most: **the seq
moves before the outcomes run**, so a second console pressing in the same frame is
refused rather than applying an irreversible outcome twice.

The choice grammar is `amd_choice`'s, unchanged - the one OU dialogue, hails and away
scenes already use - so a writer has nothing new to learn and `sbs lint` already reads
the line.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.messages import (
    message_send, message_inbox, message_choices, message_answer, message_answered,
    message_load_amd, message_deliver_due, message_ask, message_get, MAX_CHOICES)


class _Sim:
    time_tick_counter = 0


class _Page:
    def __init__(self, console, client_id=7):
        self.console = console
        self.client_id = client_id
        self.gui_task = None


class ChoiceBase(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_Sim(), sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        clear_shared()

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def ask(self, **kw):
        kw.setdefault("sender", "The Captain")
        kw.setdefault("choices", [
            {"label": "Hold", "target": "hold", "guard": None,
             "outcomes": [("signal", "held")]},
            {"label": "Break off", "target": "run", "guard": None,
             "outcomes": [("signal", "ran")]},
        ])
        return message_send("Do we hold?", **kw)


class TestOfferingAChoice(ChoiceBase):
    def test_a_message_can_carry_replies(self):
        msg = self.ask()
        self.assertEqual([c["label"] for c in message_choices(msg["id"], "helm")],
                         ["Hold", "Break off"])

    def test_a_message_without_any_behaves_as_it_always_did(self):
        msg = message_send("Just telling you.", sender="Mum")
        self.assertEqual(message_choices(msg["id"], "helm"), [])
        self.assertIsNone(message_answered(msg["id"]))

    def test_choices_are_capped(self):
        """Wider than four stops being a decision and starts being a menu -
        hail.py's HAIL_MAX_CHOICES, for the same reason."""
        msg = self.ask(choices=[f"Option {i}" for i in range(9)])
        self.assertEqual(len(message_choices(msg["id"], "helm")), MAX_CHOICES)

    def test_a_bare_label_is_a_choice(self):
        """Labels, pairs or dicts, the way hail.py accepts them."""
        msg = self.ask(choices=["Acknowledge"])
        got = message_choices(msg["id"], "helm")
        self.assertEqual(got[0]["label"], "Acknowledge")
        self.assertIsNone(got[0]["target"])

    def test_a_pair_carries_its_target(self):
        msg = self.ask(choices=[("Yes", "yes_scene")])
        self.assertEqual(message_choices(msg["id"], "helm")[0]["target"], "yes_scene")

    def test_an_answered_message_offers_nothing(self):
        """A decision already taken is not still on offer - leaving the buttons up
        invites a press that can only be refused."""
        msg = self.ask()
        message_answer(msg["id"], 0, "helm")
        self.assertEqual(message_choices(msg["id"], "helm"), [])


class TestArbitration(ChoiceBase):
    def test_answering_records_the_choice_and_who_made_it(self):
        msg = self.ask()
        message_answer(msg["id"], 0, "helm")
        self.assertEqual(message_answered(msg["id"]),
                         {"label": "Hold", "by": "helm", "at": 0})

    def test_A_SECOND_PRESS_IN_THE_SAME_FRAME_IS_REFUSED(self):
        """The property the whole design rests on. The seq moves BEFORE outcomes run,
        so the console that pressed a moment later is already stale - the outcomes
        are the part that cannot be undone."""
        msg = self.ask()
        seq = message_choices(msg["id"], "helm")[0]["seq"]
        self.assertIsNotNone(message_answer(msg["id"], 0, "helm", seq=seq))
        self.assertIsNone(message_answer(msg["id"], 1, "weapons", seq=seq))

    def test_the_first_answer_is_the_one_that_stands(self):
        msg = self.ask()
        message_answer(msg["id"], 0, "helm")
        message_answer(msg["id"], 1, "weapons")
        self.assertEqual(message_answered(msg["id"])["label"], "Hold")

    def test_an_index_that_is_not_on_offer_is_refused(self):
        msg = self.ask()
        self.assertIsNone(message_answer(msg["id"], 7, "helm"))
        self.assertIsNone(message_answered(msg["id"]))

    def test_answering_a_message_that_does_not_exist_is_refused(self):
        self.assertIsNone(message_answer(9999, 0, "helm"))

    def test_the_reply_is_posted_back_into_the_thread(self):
        """What makes it read as a conversation rather than a form."""
        msg = self.ask(to="helm")
        message_answer(msg["id"], 0, "helm")
        thread = message_inbox("helm")
        self.assertEqual(thread[0]["kind"], "reply")
        self.assertEqual(thread[0]["text"], "Hold")
        self.assertEqual(thread[0]["from"], "helm")

    def test_a_reply_goes_to_the_same_people(self):
        """A private exchange stays private; an announcement is answered in public."""
        msg = self.ask(to="helm")
        message_answer(msg["id"], 0, "helm")
        self.assertEqual(len(message_inbox("weapons")), 0)


class TestOutcomes(ChoiceBase):
    def test_a_choice_emits_its_signal(self):
        seen = []
        from sbs_utils.procedural import signal as signal_mod
        original = signal_mod.signal_emit

        def spy(name, data=None, **kw):
            seen.append(name)
            return original(name, data, **kw)
        signal_mod.signal_emit = spy
        self.addCleanup(setattr, signal_mod, "signal_emit", original)

        import sbs_utils.procedural.amd_dialogue as dlg
        dlg_original = dlg.signal_emit
        dlg.signal_emit = spy
        self.addCleanup(setattr, dlg, "signal_emit", dlg_original)

        msg = self.ask()
        message_answer(msg["id"], 0, "helm")
        self.assertIn("held", seen)

    def test_a_refused_outcome_refuses_the_pick(self):
        """A cost that cannot be afforded must not leave the message answered."""
        from sbs_utils.procedural.amd_dialogue import (
            dialogue_register_outcome, _OUTCOME_HANDLERS)
        dialogue_register_outcome("cannot", lambda a, s, args: False)
        self.addCleanup(_OUTCOME_HANDLERS.pop, "cannot", None)
        msg = self.ask(choices=[{"label": "Try", "target": None, "guard": None,
                                 "outcomes": [("cannot",)]}])
        self.assertIsNone(message_answer(msg["id"], 0, "helm"))
        self.assertIsNone(message_answered(msg["id"]))


AMD = """# [Mail](m)

## [The chief wants an answer](ask1)
---
From: Chief Anwar
To: engineering
---
The second manifold is a repair, not a part. Do I pull it now or nurse it?

- [Pull it now](pull) ; signal manifold_pulled
- [Nurse it](nurse) ; signal manifold_nursed

## [Just telling you](plain)
---
From: Mum
---
Your nan says hello.
"""


class TestAuthoredChoices(ChoiceBase):
    def load(self):
        message_load_amd(amd_document(AMD))
        message_deliver_due(now=0)

    def test_reply_lines_become_choices(self):
        self.load()
        msg = next(m for m in message_inbox("engineering")
                   if m["subject"] == "The chief wants an answer")
        self.assertEqual([c["label"] for c in message_choices(msg["id"], "engineering")],
                         ["Pull it now", "Nurse it"])

    def test_and_are_taken_OUT_of_the_prose(self):
        """A reply line is a reply, not part of the letter."""
        self.load()
        msg = next(m for m in message_inbox("engineering")
                   if m["subject"] == "The chief wants an answer")
        self.assertNotIn("[Pull it now]", msg["text"])
        self.assertTrue(msg["text"].endswith("nurse it?"))

    def test_outcomes_survive_the_round_trip(self):
        self.load()
        msg = next(m for m in message_inbox("engineering")
                   if m["subject"] == "The chief wants an answer")
        got = message_choices(msg["id"], "engineering")
        self.assertEqual(got[0]["outcomes"], [("signal", "manifold_pulled")])

    def test_a_message_with_no_reply_lines_is_untouched(self):
        self.load()
        msg = next(m for m in message_inbox("helm") if m["subject"] == "Just telling you")
        self.assertEqual(msg["text"], "Your nan says hello.")
        self.assertEqual(message_choices(msg["id"], "helm"), [])


class TestLiveAudiences(ChoiceBase):
    """`away` and `ship` are a question, not a name - who is down there changes during
    a mission, so they are answered when the inbox is READ."""

    def away(self, *client_ids):
        from sbs_utils.procedural import away as away_mod
        away_mod._TEAM.clear()
        for cid in client_ids:
            away_mod._TEAM[cid] = [1000 + cid]
        self.addCleanup(away_mod._TEAM.clear)

    def test_a_note_to_the_away_team_reaches_a_console_that_is_down_there(self):
        self.away(7)
        message_send("Watch your footing.", to="away", sender="The Captain")
        FrameContext.page = _Page("helm", client_id=7)
        self.assertEqual(len(message_inbox()), 1)

    def test_and_not_a_console_that_is_not(self):
        self.away(7)
        message_send("Watch your footing.", to="away", sender="The Captain")
        FrameContext.page = _Page("helm", client_id=9)
        self.assertEqual(message_inbox(), [])

    def test_a_note_to_the_ship_reaches_the_ones_still_aboard(self):
        self.away(7)
        message_send("We are still here.", to="ship", sender="Away Team")
        FrameContext.page = _Page("helm", client_id=9)
        self.assertEqual(len(message_inbox()), 1)
        FrameContext.page = _Page("helm", client_id=7)
        self.assertEqual(message_inbox(), [])

    def test_the_answer_follows_the_team_changing(self):
        """Resolved at read time, which is the whole point: a note written before a
        console beamed down still finds it afterwards."""
        message_send("Watch your footing.", to="away", sender="The Captain")
        FrameContext.page = _Page("helm", client_id=7)
        self.assertEqual(message_inbox(), [])
        self.away(7)
        self.assertEqual(len(message_inbox()), 1)

    def test_the_away_console_name_alone_is_enough(self):
        """gui_console_enter sets the console to "away" when it morphs one."""
        message_send("Watch your footing.", to="away", sender="The Captain")
        self.assertEqual(len(message_inbox("away")), 1)


class TestAsk(ChoiceBase):
    def test_message_ask_returns_a_promise_that_settles_on_the_answer(self):
        prom = message_ask("Do we hold?", to="helm", sender="The Captain",
                           choices=["Hold", "Break off"])
        self.assertFalse(prom.done())
        msg = message_inbox("helm")[0]
        message_answer(msg["id"], 0, "helm")
        self.assertTrue(prom.done())
        self.assertEqual(prom.result()["label"], "Hold")   # result() is a method

    def test_an_unanswered_ask_leaves_the_promise_open(self):
        """Documented: compose it with a timeout when that matters."""
        prom = message_ask("Anyone?", sender="The Captain", choices=["Yes"])
        self.assertFalse(prom.done())


if __name__ == "__main__":
    unittest.main()


def _scene_doc(key="door", body=None):
    """The shape dialogue_get wants: key -> node, as dialogue_scenes() produces."""
    return {key: {"key": key, "display_text": key, "data": {}, "children": [],
                  "description": body or (
                      "The door is shut. Something behind it is breathing.\n"
                      "\n"
                      "- [Knock](knocked)\n"
                      "- [Listen first](listened)\n")}}


class TestAwayBeatsReachTheInbox(ChoiceBase):
    """The away team's only channel has always been the shared main screen, read-only.
    Mirroring each beat gives them a transcript they can scroll and a place to answer
    from, without touching the away console - which keeps rendering the scene as it
    always did, so `LandingParty` is unaffected.
    """

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural import away as away_mod
        self.away_mod = away_mod
        away_mod.away_clear()
        away_mod._TEAM.clear()
        self.addCleanup(away_mod.away_clear)
        self.addCleanup(away_mod._TEAM.clear)
        self.addCleanup(away_mod.away_mirror_to_inbox, True)

    def open(self, **kw):
        return self.away_mod.away_scene_begin(_scene_doc(), "door",
                                              speaker=kw.get("speaker", "The Keeper"))

    def test_a_beat_arrives_as_a_message(self):
        self.open()
        got = message_inbox("away")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "scene")
        self.assertEqual(got[0]["from"], "The Keeper")
        self.assertTrue(got[0]["text"].startswith("The door is shut"))

    def test_it_is_addressed_to_the_away_team_only(self):
        """A bridge console is not on the surface and should not read its transcript."""
        self.open()
        self.assertEqual(message_inbox("helm"), [])

    def test_it_carries_the_scene_key(self):
        self.open()
        self.assertEqual(message_inbox("away")[0]["scene"], "door")

    def test_it_carries_NO_choices_of_its_own(self):
        """The replies differ per character and away_answer already arbitrates them.
        A copy on the message would give one scene two competing paths."""
        self.open()
        self.assertEqual(message_inbox("away")[0]["choices"], [])
        self.assertEqual(message_choices(message_inbox("away")[0]["id"], "away"), [])

    def test_each_beat_adds_to_the_transcript(self):
        self.open()
        self.open()
        self.assertEqual(len(message_inbox("away")), 2)

    def test_a_mission_can_turn_the_mirror_off(self):
        self.away_mod.away_mirror_to_inbox(False)
        self.open()
        self.assertEqual(message_inbox("away"), [])

    def test_the_away_console_still_gets_its_own_choices(self):
        """The regression that matters: mirroring is additive, and away play is
        unchanged for a mission that never opens the PADD."""
        self.away_mod._TEAM[7] = [1]
        self.open()
        self.assertEqual(self.away_mod.away_scene(), "door")
        self.assertTrue(self.away_mod.away_line())
