"""A word in `mission.amd` is a promise about `story.mast`. Lint has to check the promise.

Found by the lesson "Roles and signals", which changes nothing in the story but words
inside quote marks. Thirty such mistakes linted `clean` with both logs empty:

  * A NOTE counted as code. The starter story explains its signal line in a comment that
    holds `signal_emit("derelict_found")`, so the signal was "sent" whatever the working
    line said.
  * A plain `signal_emit("x")` counted as sending `x` to a quest. A quest hears only
    `signal_emit("quest_signal", {"SIGNAL_NAME": "x"})`.
  * `Ghost_Ship_Found` in BOTH files never fired: the `.amd` side is folded to small
    letters as it is read, and the story's side was compared as typed.
  * `Done when: signal derelict found` was reported as waiting for `derelict`; the game
    finishes it on `derelict_found`.

And from "Lint is your editor": a step that waits to be revealed, with the `Then: reveal`
that named it deleted, was `clean`; and `Then: reveal arc / step` revealed nothing.

    python -m unittest tests.test_story_words_match
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.quest import quest_add, quest_get_state, QuestState

MISSION = """# [Sample Mission](sample_mission)

## [Quests](quests)

### [First Contact](first_contact)
---
Scope: shared
Starts when: at once
---
A derelict has drifted into the sector.

#### [Find the Derelict](find)
---
Scope: shared
Starts when: at once
Done when: signal derelict_found
Then: reveal first_contact/study
---
Fly out and locate the drifting hulk.

#### [Study the Derelict](study)
---
Scope: shared
Starts when: revealed
Done when: signal derelict_studied
---
Science should take a full scan of the hull.
"""

STORY = '''# The story says the word out loud when the ship reaches the hulk. A plain
# signal_emit("derelict_found") would reach a route and no quest.
== watch ==
    await delay_sim(1)
    signal_emit("quest_signal", {"SIGNAL_NAME": "derelict_found"})
    signal_emit("quest_signal", {"SIGNAL_NAME": "derelict_studied"})
    ->END
'''


def findings(mission=MISSION, story=STORY, code=None):
    found = amd_lint(content=mission, mast_sources=[story])
    return [f for f in found if code is None or f.code == code]


def story(old, new):
    assert STORY.count(old) == 1, old
    return STORY.replace(old, new)


class TheStarterIsClean(unittest.TestCase):
    def test_no_finding(self):
        self.assertEqual([str(f) for f in findings()], [])


class ANoteIsNotCode(unittest.TestCase):
    def test_a_misspelled_working_line_is_seen_past_the_note_above_it(self):
        found = findings(story=story('"SIGNAL_NAME": "derelict_found"', '"SIGNAL_NAME": "derelict_fond"'),
                         code="unfired-signal")
        self.assertEqual(len(found), 1)
        self.assertIn("`derelict_found`", found[0].message)

    def test_a_signal_renamed_in_the_notes_only(self):
        mission = MISSION.replace("signal derelict_found", "signal ghost_ship_found")
        notes = STORY.replace('signal_emit("derelict_found")', 'signal_emit("ghost_ship_found")')
        self.assertEqual(len(findings(mission, notes, "unfired-signal")), 1)


class WhatAQuestHears(unittest.TestCase):
    def test_a_plain_signal_emit_is_not_heard_and_the_line_to_write_is_given(self):
        plain = story('signal_emit("quest_signal", {"SIGNAL_NAME": "derelict_found"})',
                      'signal_emit("derelict_found")')
        found = findings(story=plain, code="unfired-signal")
        self.assertEqual(len(found), 1)
        self.assertIn("plain `signal_emit`", found[0].message)
        self.assertIn('{"SIGNAL_NAME": "derelict_found"}', found[0].message)

    def test_a_mission_that_hands_every_signal_on_is_not_second_guessed(self):
        # Dawnline observes every signal and calls quest_on_signal(name) with it.
        forwarder = "def _lp_quest_signal(name, data):\n    quest_on_signal(name)\n"
        plain = story('signal_emit("quest_signal", {"SIGNAL_NAME": "derelict_found"})',
                      'signal_emit("derelict_found")')
        found = amd_lint(content=MISSION, mast_sources=[plain, forwarder])
        self.assertNotIn("unfired-signal", [f.code for f in found])

    def test_the_stock_route_is_not_a_forwarder(self):
        stock = "//shared/signal/quest_signal\n    quest_on_signal(SIGNAL_NAME)\n    ->END\n"
        plain = story('signal_emit("quest_signal", {"SIGNAL_NAME": "derelict_found"})',
                      'signal_emit("derelict_found")')
        found = amd_lint(content=MISSION, mast_sources=[plain, stock])
        self.assertIn("unfired-signal", [f.code for f in found])

    def test_the_other_two_ways_to_reach_a_quest_count(self):
        for line in ('quest_on_signal("derelict_found")',
                     'quest_credit_signal(SHIP_ID, "derelict_found")'):
            with self.subTest(line=line):
                text = story('signal_emit("quest_signal", {"SIGNAL_NAME": "derelict_found"})', line)
                self.assertEqual(findings(story=text, code="unfired-signal"), [])


class OneSpellingOfASignal(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        quest_add(Agent.SHARED_ID, "find", "Find", "", state=QuestState.ACTIVE,
                  data={"on_signal": {"name": "derelict_found"}})

    def done(self):
        return quest_get_state(Agent.SHARED_ID, "find") == QuestState.COMPLETE

    def test_capitals_in_the_story_still_finish_the_quest(self):
        QD.quest_on_signal("Derelict_Found")
        self.assertTrue(self.done())

    def test_spaces_in_the_story_still_finish_the_quest(self):
        QD.quest_on_signal("derelict found")
        self.assertTrue(self.done())

    def test_another_word_does_not(self):
        QD.quest_on_signal("derelict_fond")
        self.assertFalse(self.done())

    def test_the_owner_scoped_form_folds_too(self):
        QD.quest_credit_signal(Agent.SHARED_ID, "Derelict_Found")
        self.assertTrue(self.done())

    def test_lint_agrees_with_the_game(self):
        caps = story('"SIGNAL_NAME": "derelict_found"', '"SIGNAL_NAME": "Derelict_Found"')
        self.assertEqual(findings(story=caps, code="unfired-signal"), [])
        spaced = MISSION.replace("signal derelict_found", "signal derelict found")
        self.assertEqual(findings(spaced, code="unfired-signal"), [])

    def test_a_signal_sent_with_no_name_is_said(self):
        heard = []

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        handler = _Listen()
        logging.getLogger("mast.runtime").addHandler(handler)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, handler)
        QD.quest_on_signal(None)
        self.assertFalse(self.done())
        self.assertEqual(len([l for l in heard if "no name" in l]), 1)


class AStepNothingReveals(unittest.TestCase):
    NO_THEN = MISSION.replace("Then: reveal first_contact/study\n", "")

    def test_the_then_line_deleted(self):
        found = findings(self.NO_THEN, code="never-revealed")
        self.assertEqual(len(found), 1)
        self.assertIn("Study the Derelict", found[0].message)
        self.assertIn("Then: reveal first_contact/study", found[0].message)

    def test_the_starter_has_none(self):
        self.assertEqual(findings(code="never-revealed"), [])

    def test_an_answer_that_accepts_it_counts(self):
        text = self.NO_THEN + ("\n## [Dialogue](dialogue)\n\n### [A Call](call)\n---\nSpeaker: rook\n---\n"
                               "Hello.\n\n- [Take it]() ; accepts first_contact/study\n")
        self.assertEqual(findings(text, code="never-revealed"), [])

    def test_a_story_that_names_it_counts(self):
        text = STORY + '    quest_mark_active(SHARED, "first_contact/study")\n'
        self.assertEqual(findings(self.NO_THEN, text, code="never-revealed"), [])

    def test_one_file_alone_is_not_judged(self):
        found = amd_lint(content=self.NO_THEN, cross_file=False)
        self.assertNotIn("never-revealed", [f.code for f in found])


class APathWithSpacesRoundItsSlash(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        quest_add(Agent.SHARED_ID, "first_contact", "First Contact", "", state=QuestState.ACTIVE)
        quest_add(Agent.SHARED_ID, "first_contact/study", "Study", "", state=QuestState.SECRET)

    def test_the_game_reveals_the_step(self):
        QD.quest_reveal(Agent.SHARED_ID, "first_contact / study")
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "first_contact/study"), QuestState.ACTIVE)


if __name__ == "__main__":
    unittest.main()
