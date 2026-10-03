"""The mistakes a first quest chain makes, each of which used to be silent.

Found by the lesson "Chains and trees": a writer turns one quest into an arc with steps,
and every one of these linted clean and failed quietly in play.

  * Steps typed under the WRONG heading. `Then: reveal salvage/home` was "resolved"
    because a `home` existed somewhere in the file, the reveal found nothing, the arc was
    left with one nested step - and the game was WON when that step finished. Seen in the
    engine, 2026-10-03.
  * `Part of: salvge` - only the older spelling `Parent:` was checked.
  * A third level of nesting was dropped by `quest_folder`, which never descended.
  * `1 hour` was one minute; `2 minutes 30 seconds` was two SECONDS; `90 sec`, `10m` and
    `after 10 minutes` were no clock at all.
  * `Done when: ten minutes`, `Fails when: reach station 1000`, `Starts when: reveal`:
    dropped without a word.
  * Starting a quest that does not exist announced `quest_started` for it.

    python -m unittest tests.test_quest_chain_mistakes
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
from sbs_utils.procedural.amd import amd_duration_parts, amd_duration_seconds, amd_is_duration
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_quest import amd_trigger
from sbs_utils.procedural.quest import quest_add, quest_get, QuestState

ARC = """# [Mission](mission)

## [Quests](quests)

### [Salvage Run](salvage)
---
Arc
Scope: shared
Starts when: at once
Fails when: 10 minutes
---
Bring the log home.

#### [Close Inspection](approach)
---
Scope: shared
Starts when: at once
Done when: reach derelict 500
Then: reveal salvage/home
Part of: salvage
Required: true
---
Go and look.

#### [Bring the Log Home](home)
---
Scope: shared
Starts when: revealed
Done when: reach station 1000
Part of: salvage
Required: true
---
Take it back.
"""


def _codes(text, **kw):
    return [f.code for f in amd_lint(content=text, cross_file=False, **kw)]


def _swap(old, new, text=ARC):
    assert text.count(old) == 1, old
    return text.replace(old, new)


class TheLessonsArcIsCleanTests(unittest.TestCase):
    def test_nothing_is_reported(self):
        self.assertEqual(_codes(ARC), [])


class AStepUnderTheWrongHeadingTests(unittest.TestCase):
    def test_a_step_outside_its_arc_does_not_resolve_the_reveal(self):
        """`home` exists - but not under `salvage`, which is in this file."""
        text = _swap("#### [Bring the Log Home](home)", "### [Bring the Log Home](home)")
        self.assertIn("dangling-reveal", _codes(text))

    def test_even_when_the_mission_knows_the_leaf(self):
        """`sbs lint` hands every key in the mission in as known, this file's included -
        which is what made the wrong-heading case resolve."""
        text = _swap("#### [Bring the Log Home](home)", "### [Bring the Log Home](home)")
        self.assertIn("dangling-reveal", _codes(text, known_keys={"home", "salvage"}))

    def test_a_path_into_another_file_is_still_given_the_benefit_of_the_doubt(self):
        text = _swap("Then: reveal salvage/home", "Then: reveal other_arc/home")
        self.assertNotIn("dangling-reveal",
                         _codes(text, known_keys={"other_arc", "home"}))

    def test_part_of_is_checked_like_parent(self):
        text = ARC.replace("Part of: salvage\nRequired: true\n---\nGo and look.",
                           "Part of: salvge\nRequired: true\n---\nGo and look.")
        self.assertIn("dangling-parent", _codes(text))

    def test_the_older_spelling_still_is(self):
        text = ARC.replace("Part of: salvage\nRequired: true\n---\nGo and look.",
                           "Parent: salvge\nRequired: true\n---\nGo and look.")
        self.assertIn("dangling-parent", _codes(text))


class TriggersTheGameCannotWatchTests(unittest.TestCase):
    def test_a_time_written_in_words(self):
        self.assertIn("unknown-trigger",
                      _codes(_swap("Fails when: 10 minutes", "Fails when: ten minutes")))

    def test_a_done_when_that_is_not_a_trigger(self):
        self.assertIn("unknown-trigger",
                      _codes(_swap("Done when: reach station 1000", "Done when: get home")))

    def test_a_fail_trigger_nothing_watches(self):
        self.assertIn("unsupported-fail-trigger",
                      _codes(_swap("Fails when: 10 minutes", "Fails when: reach station 1000")))

    def test_reveal_for_revealed(self):
        self.assertIn("unknown-trigger",
                      _codes(_swap("Starts when: revealed", "Starts when: reveal")))

    def test_then_written_twice(self):
        text = _swap("Then: reveal salvage/home\n",
                     "Then: reveal salvage/home\nThen: signal log_found\n")
        self.assertIn("repeated-then", _codes(text))

    def test_every_supported_spelling_is_quiet(self):
        for value in ("signal reactor_gone", "all dead raider", "5 minutes", "90 sec",
                      "1 hour", "2 minutes 30 seconds", "10m"):
            codes = _codes(_swap("Fails when: 10 minutes", "Fails when: " + value))
            self.assertEqual([c for c in codes if "trigger" in c], [], value)


class DurationTests(unittest.TestCase):
    def test_an_hour_is_sixty_minutes(self):
        self.assertEqual(amd_duration_seconds("1 hour"), 3600)
        self.assertEqual(amd_duration_parts("2 hours"), (120, "minutes"))

    def test_minutes_and_seconds_add_up(self):
        self.assertEqual(amd_duration_seconds("2 minutes 30 seconds"), 150)
        self.assertEqual(amd_duration_seconds("1h 30m"), 5400)

    def test_short_spellings_have_a_clock(self):
        self.assertEqual(amd_trigger("90 sec"), ("after", {"seconds": 90}))
        self.assertEqual(amd_trigger("10m"), ("after", {"minutes": 10}))
        self.assertEqual(amd_trigger("after 10 minutes"), ("after", {"minutes": 10}))

    def test_what_always_worked_still_reads_the_same(self):
        self.assertEqual(amd_duration_parts("6 minutes"), (6, "minutes"))
        self.assertEqual(amd_duration_parts("90 seconds"), (90, "seconds"))
        self.assertEqual(amd_duration_parts("2"), (2, "minutes"))
        self.assertEqual(amd_duration_parts("20m"), (20, "minutes"))
        self.assertEqual(amd_duration_parts("2h"), (120, "minutes"))
        self.assertEqual(amd_trigger("5 minutes"), ("after", {"minutes": 5}))

    def test_words_are_not_a_time(self):
        self.assertIsNone(amd_trigger("ten minutes"))
        self.assertFalse(amd_is_duration("ten minutes"))
        self.assertFalse(amd_is_duration("reach 6, 4"))


class NestingTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)

    def test_a_third_level_is_kept(self):
        quest_add(Agent.SHARED_ID, "arc", "Arc", "", state=QuestState.ACTIVE)
        quest_add(Agent.SHARED_ID, "arc/step", "Step", "", state=QuestState.ACTIVE)
        quest_add(Agent.SHARED_ID, "arc/step/part", "Part", "", state=QuestState.ACTIVE)
        self.assertIsNotNone(quest_get(Agent.SHARED_ID, "arc/step/part"))
        self.assertIsNone(quest_get(Agent.SHARED_ID, "step"))       # not at the top

    def test_a_missing_parent_is_none_not_a_crash(self):
        self.assertIsNone(quest_get(Agent.SHARED_ID, "nope/step/part"))


class StartingAQuestThatIsNotThereTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.heard = []
        heard = self.heard

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        self._h = _Listen()
        logging.getLogger("mast.runtime").addHandler(self._h)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, self._h)

    def test_it_says_so_and_starts_nothing(self):
        QD.quest_mark_active(Agent.SHARED_ID, "salvage/home")
        self.assertEqual(len([l for l in self.heard if "salvage/home" in l]), 1)
        self.assertIsNone(quest_get(Agent.SHARED_ID, "salvage/home"))


if __name__ == "__main__":
    unittest.main()
