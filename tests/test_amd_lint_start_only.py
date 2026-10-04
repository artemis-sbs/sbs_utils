"""A quest that a trigger starts and nothing can finish.

Found by the lesson "Quests through a ruin". `When:` is short for `Starts when:`. It used
to be the trigger that COMPLETED a step, and a chain written that way - the way the shipped
episode template still shows it -

    #### [Storm's First Lead](ep1_go)
    ---
    State: secret
    When: reach 2, -1
    Then: reveal beacon_arc/ep1_approach
    ---

starts when the ship arrives and then stays active for good: the next step is never
revealed, a reward on it is never paid, lint was clean and the log empty.

The lint test reads AMD text; the driver test grants the same text and fires its trigger,
so the two cannot drift.

    python -m unittest tests.test_amd_lint_start_only
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.quest import QuestState, quest_get_state

CHAIN = """# [Mission](mission)

## [Quests](quests)

### [The Beacon](arc)
---
Scope: shared
State: active
---
An arc. It finishes when its steps do.

#### [Contact Storm](briefing)
---
Scope: shared
State: active
{trigger}: signal storm_briefed
Then: reveal arc/lead
Reward: 150 credits
---
Hail her.

#### [The Lead](lead)
---
Scope: shared
Starts when: revealed
Done when: signal lead_found
---
Follow it.
"""


def found(text):
    return [f for f in amd_lint(file_path="mission.amd", content=text, cross_file=False)
            if f.code == "quest-never-finishes"]


class StartOnlyLint(unittest.TestCase):
    def test_when_with_no_done_when(self):
        got = found(CHAIN.format(trigger="When"))
        self.assertEqual(len(got), 1)
        self.assertIn("Contact Storm", got[0].message)
        self.assertIn("Done when: signal storm_briefed", got[0].message)
        self.assertIn("`Then:` never happens", got[0].message)
        self.assertIn("never paid", got[0].message)

    def test_starts_when_with_no_done_when_is_the_same_mistake(self):
        self.assertEqual(len(found(CHAIN.format(trigger="Starts when"))), 1)

    def test_done_when_is_what_was_meant(self):
        self.assertEqual(found(CHAIN.format(trigger="Done when")), [])

    def test_a_quest_with_both_is_fine(self):
        text = CHAIN.format(trigger="Starts when").replace(
            "Then: reveal arc/lead", "Done when: signal call_over\nThen: reveal arc/lead")
        self.assertEqual(found(text), [])

    def test_revealed_accepted_and_at_once_are_not_triggers(self):
        for value in ("revealed", "accepted", "at once"):
            with self.subTest(value=value):
                text = CHAIN.format(trigger="Starts when").replace(
                    "Starts when: signal storm_briefed", "Starts when: " + value)
                self.assertEqual(found(text), [])

    def test_a_cue_that_starts_to_do_something_is_left_alone(self):
        """A beat on a start trigger with an `Action:` and nothing waiting on its end."""
        cue = ("\n#### [Marker One](marker_one)\n---\nBeat\n"
               "Starts when: reach altar 600\nAction:\n  - rook hails rook_altar\n---\n")
        self.assertEqual(found(CHAIN.format(trigger="Done when") + cue), [])
        # ... but the same cue with a `Then:` is a chain that stops there.
        broken = cue.replace("Action:", "Then: reveal arc/lead\nAction:")
        self.assertEqual(len(found(CHAIN.format(trigger="Done when") + broken)), 1)

    def test_an_arc_is_left_alone(self):
        text = CHAIN.format(trigger="Done when").replace(
            "State: active\n---\nAn arc.", "When: signal go\n---\nAn arc.")
        self.assertEqual(found(text), [])


class WhatTheGameDoes(unittest.TestCase):
    """The reason for the warning, measured: the same text, granted, its trigger fired."""

    def play(self, trigger):
        reset_mock(sbs)
        sbs.resume_sim()
        doc = amd_document(CHAIN.format(trigger=trigger), data_parser=amd_quest_data)
        QD.quest_grant_amd(Agent.SHARED_ID, amd_section(doc, "quests"))
        QD.quest_on_signal("storm_briefed")
        QD.quest_on_signal("storm_briefed")
        return (quest_get_state(Agent.SHARED_ID, "arc/briefing"),
                quest_get_state(Agent.SHARED_ID, "arc/lead"))

    def test_when_starts_it_and_it_never_finishes(self):
        briefing, lead = self.play("When")
        self.assertEqual(briefing, QuestState.ACTIVE)
        self.assertEqual(lead, QuestState.SECRET)          # never revealed

    def test_done_when_finishes_it_and_reveals_the_next(self):
        briefing, lead = self.play("Done when")
        self.assertEqual(briefing, QuestState.COMPLETE)
        self.assertEqual(lead, QuestState.ACTIVE)


if __name__ == "__main__":
    unittest.main()
