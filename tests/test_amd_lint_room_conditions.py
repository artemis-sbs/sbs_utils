"""A condition in a boarding room that nobody can ever meet, and says nothing.

Found by the lesson "Checkpoint: a short boarding quest". A condition is a name, or
`name op number`. Everything else a writer reaches for is read as ONE LONG NAME - a job
nobody holds - so the choice is offered to nobody, lint was clean, and the log was empty:

    if medical and learned >= 2     if medical or engineering     if not medical
    if alive (a fact)               if learned alive              if learned 3
    if hale / if Dr Hale (a person)

Also here: a `%` line broken in two (the room says one half or the other), an answer that
`accepts` a quest already running, and `Learned` with a capital, which the GAME now reads.

    python -m unittest tests.test_amd_lint_room_conditions
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from sbs_utils.procedural.amd_lint import amd_lint

GOOD = """# [Mission](mission)

## [Quests](quests)

### [Stand By the Sleepers](stand_by)
---
Scope: shared
Starts when: revealed
Done when: 30 seconds
---
Stay with them.

## [The Watch](watch)
---
crew
Ship: Artemis
---

### [Chief Okoro](okoro)
---
Console: engineering
Roles: engineering
---

### [Dr Ines Hale](hale)
---
Console: science
Roles: medical
---

## [Rooms](boarding)

### [The Spine](spine)
% One long corridor, bow to stern, frost on every hatch.

- [Read the berth monitors](spine) if medical ; learn alive
- [Read the engine log](spine) if engineering ; learn rationed
- [Open the captain's hatch](cabin) if learned >= 2
- [Return to the ship]()

### [The Captain's Cabin](cabin)
% The captain's last order is taped to the desk.

- [Throw the switch and wake them]() ; accepts stand_by
"""

MINE = ("guard-joined", "guard-learned-shape", "guard-names-a-fact", "guard-names-a-person",
        "line-wrapped", "outcome-accepts-running")
HATCH = "if learned >= 2"


def codes(text):
    return sorted(f.code for f in amd_lint(file_path="mission.amd", content=text,
                                            cross_file=False) if f.code in MINE)


def hatch(condition):
    assert GOOD.count(HATCH) == 1
    return GOOD.replace(HATCH, "if " + condition)


class ConditionsNobodyMeets(unittest.TestCase):
    def test_the_scene_as_written_is_clean(self):
        self.assertEqual(codes(GOOD), [])

    def test_two_conditions_joined(self):
        for condition in ("medical and learned >= 2", "medical or engineering", "not medical",
                          "not learned", "medical and engineering"):
            with self.subTest(condition=condition):
                self.assertEqual(codes(hatch(condition)), ["guard-joined"])

    def test_learned_with_a_number_needs_its_sign(self):
        """`if learned alive` IS a condition since 2026-10-09 (one fact, by name - see
        test_boarding_learned_fact). A bare number after it is still a slipped sign, and
        one fact is never two."""
        for condition in ("learned 3", "learned alive >= 2"):
            with self.subTest(condition=condition):
                self.assertEqual(codes(hatch(condition)), ["guard-learned-shape"])
        self.assertEqual(codes(hatch("learned alive")), [])
        self.assertEqual(codes(hatch("learned rationed >= 1")), [])

    def test_a_fact_asked_for_by_name(self):
        self.assertEqual(codes(hatch("alive")), ["guard-names-a-fact"])
        self.assertEqual(codes(hatch("alive >= 1")), ["guard-names-a-fact"])

    def test_a_person_where_a_job_goes(self):
        for condition in ("hale", "Dr Ines Hale", "Hale", "okoro"):
            with self.subTest(condition=condition):
                self.assertEqual(codes(hatch(condition)), ["guard-names-a-person"])

    def test_what_a_condition_can_be_is_left_alone(self):
        for condition in ("learned >= 2", "Learned >= 2", "medical", "Medical", "engineering",
                          "skill science >= 3", "security", "credits >= 200", "briefed"):
            with self.subTest(condition=condition):
                self.assertEqual(codes(hatch(condition)), [])

    def test_a_gated_line_is_judged_the_same_way(self):
        text = GOOD.replace("% One long corridor", "%{medical and learned < 2} One long corridor")
        self.assertEqual(codes(text), ["guard-joined"])


class OtherRoomMistakes(unittest.TestCase):
    def test_a_line_broken_in_two(self):
        text = GOOD.replace("% One long corridor, bow to stern, frost on every hatch.",
                            "% One long corridor, bow to stern,\nfrost on every hatch.")
        self.assertEqual(codes(text), ["line-wrapped"])

    def test_two_lines_each_with_its_mark_are_two_lines_on_purpose(self):
        text = GOOD.replace("% One long corridor, bow to stern, frost on every hatch.",
                            "% One long corridor, bow to stern.\n% Frost on every hatch.")
        self.assertEqual(codes(text), [])

    def test_an_ending_that_was_already_running(self):
        text = GOOD.replace("Starts when: revealed", "Starts when: at once")
        self.assertEqual(codes(text), ["outcome-accepts-running"])

    def test_a_quest_on_offer_may_be_accepted(self):
        self.assertEqual(codes(GOOD.replace("Starts when: revealed\n", "")), [])


class TheGameReadsLearnedInAnyCapitals(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs
        from sbs_utils.helpers import Context, FakeEvent, FrameContext
        from sbs_utils.procedural import amd_dialogue as D
        from sbs_utils.procedural import boarding as A
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.A, self.D = A, D
        A.boarding_clear()
        prev = D._METRIC_RESOLVER
        A.boarding_metric_install()
        self.addCleanup(D.dialogue_set_metric_resolver, prev)
        self.addCleanup(A.boarding_clear)

    def test_a_capital_does_not_shut_the_door(self):
        A, D = self.A, self.D
        D.dialogue_apply(None, None, [["learn", "alive"], ["learn", "rationed"]])
        self.assertEqual(A.boarding_learned(), 2)
        for word in ("learned", "Learned", "LEARNED"):
            with self.subTest(word=word):
                self.assertTrue(D.dialogue_guard_ok(word + " >= 2", None, None))
                self.assertFalse(D.dialogue_guard_ok(word + " < 2", None, None))


if __name__ == "__main__":
    unittest.main()
