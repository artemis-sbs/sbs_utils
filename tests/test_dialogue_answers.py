"""An answer that does nothing now says so - in lint, and in the log.

Found by the lesson "Dialogue, part 2": the crew answers a call, and an answer can take a
job, finish a step or lead to another scene. Every one of these linted clean, ran with an
empty log, and did something other than it read as:

  * a guard on an answer was never true in a plain mission - nothing answered `if tsn` or
    `if learned >= 1` until a boarding visit happened to install the resolver;
  * `; accepts tag_hulkk` (no such quest), `; completes study` (a step without its arc)
    and `; reveal tag_hulk` (the wrong verb) did nothing - and the driver's one sentence
    about it went to a logger nobody reads;
  * `- [Not now.]` with no round brackets, `* [..](..)`, and an outcome on a line of its
    own were SPOKEN by the caller;
  * `- [..]() accepts tag_hulk` (no `;`) threw the outcome away;
  * a reply scene with one hash too many removed the scene above it from the game;
  * an answer with curly brackets in its words was a NameError when the list was drawn.

    python -m unittest tests.test_dialogue_answers
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_lint import amd_lint

MISSION = """# [Sample Mission](sample_mission)

## [Quests](quests)

### [First Contact](first_contact)
---
Arc
Scope: shared
Starts when: at once
---
Find her.

#### [Study the Derelict](study)
---
Scope: shared
Starts when: at once
Done when: signal derelict_scanned
---
Scan her.

### [Tag the Hulk](tag_hulk)
---
Scope: shared
Starts when: accepted
Done when: 30 seconds
---
Set a beacon.

## [Characters](characters)

### [Harbormaster Quill](quill)
---
Face: terran_female
---

## [Dialogue](dialogue)

### [About that hulk](quill_hello)
---
Speaker: quill
---
% Artemis, DS 1. What do you see out there?

- [She is cold. No power.](quill_offer)
- [Not now, DS 1. Artemis out.]()

### [The Offer](quill_offer)
---
Speaker: quill
---
% Tag her for us and there is a hundred in it.

- [We will tag her.]() ; accepts tag_hulk
- [Find someone else, DS 1.]()
"""

TAKE = "- [We will tag her.]() ; accepts tag_hulk"
CODES = ("choice-shape", "choice-tail-ignored", "outcome-quest-missing",
         "outcome-quest-path", "outcome-quest-verb", "scene-nested")


def _codes(text):
    return [f.code for f in amd_lint(content=text, cross_file=False) if f.code in CODES]


def _swap(old, new, text=MISSION):
    assert text.count(old) == 1, old
    return text.replace(old, new)


class TheLessonsFileIsCleanTests(unittest.TestCase):
    def test_nothing_is_reported(self):
        self.assertEqual([f.code for f in amd_lint(content=MISSION, cross_file=False)], [])


class AnAnswerReadAsSomethingElseTests(unittest.TestCase):
    def test_no_round_brackets(self):
        self.assertIn("choice-shape",
                      _codes(_swap("- [Find someone else, DS 1.]()", "- [Find someone else, DS 1.]")))

    def test_a_star_for_the_dash(self):
        self.assertIn("choice-shape",
                      _codes(_swap("- [Find someone else, DS 1.]()", "* [Find someone else, DS 1.]()")))

    def test_an_outcome_on_a_line_of_its_own(self):
        text = _swap(TAKE, "- [We will tag her.]()\n; accepts tag_hulk")
        self.assertIn("choice-shape", _codes(text))

    def test_an_outcome_with_no_semicolon(self):
        self.assertIn("choice-tail-ignored",
                      _codes(_swap(TAKE, "- [We will tag her.]() accepts tag_hulk")))

    def test_a_condition_is_not_a_tail(self):
        self.assertEqual(_codes(_swap(TAKE, "- [We will tag her.]() if tsn ; accepts tag_hulk")), [])

    def test_a_spoken_line_with_a_dash_in_it_is_left_alone(self):
        text = _swap("% Tag her for us and there is a hundred in it.",
                     "% Tag her for us - there is a hundred in it.")
        self.assertEqual(_codes(text), [])


class AnOutcomeSentAtNothingTests(unittest.TestCase):
    def test_a_misspelled_quest(self):
        self.assertIn("outcome-quest-missing",
                      _codes(_swap(TAKE, TAKE.replace("tag_hulk", "tag_hulkk"))))

    def test_the_name_for_the_key(self):
        self.assertIn("outcome-quest-missing",
                      _codes(_swap(TAKE, TAKE.replace("accepts tag_hulk", "accepts Tag the Hulk"))))

    def test_no_quest_at_all(self):
        self.assertIn("outcome-quest-missing",
                      _codes(_swap(TAKE, TAKE.replace("accepts tag_hulk", "accepts"))))

    def test_a_step_without_its_arc(self):
        found = [f for f in amd_lint(content=_swap(TAKE, TAKE.replace("accepts tag_hulk", "completes study")),
                                     cross_file=False) if f.code == "outcome-quest-path"]
        self.assertEqual(len(found), 1)
        self.assertIn("first_contact/study", found[0].message)

    def test_the_full_path_is_quiet(self):
        text = _swap(TAKE, TAKE.replace("accepts tag_hulk", "completes first_contact/study"))
        self.assertEqual(_codes(text), [])

    def test_reveal_for_accepts(self):
        self.assertIn("outcome-quest-verb",
                      _codes(_swap(TAKE, TAKE.replace("accepts tag_hulk", "reveal tag_hulk"))))


class ASceneUnderASceneTests(unittest.TestCase):
    def test_one_hash_too_many(self):
        found = [f for f in amd_lint(content=_swap("### [The Offer](quill_offer)", "#### [The Offer](quill_offer)"),
                                     cross_file=False) if f.code == "scene-nested"]
        self.assertEqual(len(found), 1)
        self.assertIn("About that hulk", found[0].message)

    def test_a_section_with_notes_under_its_heading_is_not_a_scene(self):
        text = _swap("## [Dialogue](dialogue)\n", "## [Dialogue](dialogue)\nWhat Quill says, and when.\n")
        self.assertEqual(_codes(text), [])


class TheStockGuardWordsTests(unittest.TestCase):
    """`if tsn` and `if learned >= 1` are answerable once a scene is registered - not
    only after a boarding visit."""

    def setUp(self):
        reset_mock(sbs)
        A.boarding_clear()
        self.addCleanup(A.boarding_clear)
        # Whatever an earlier test in the same process left installed is not this test's
        # subject: start from a mission that has answered nothing yet, and put it back.
        was = D._METRIC_RESOLVER
        D.dialogue_set_metric_resolver(None)
        self.addCleanup(D.dialogue_set_metric_resolver, was)

    def test_no_resolver_until_a_scene_is_registered(self):
        self.assertIsNone(D._METRIC_RESOLVER)

    def test_registering_scenes_installs_it(self):
        D.dialogue_register_scenes(amd_section(amd_document(MISSION), "dialogue"))
        self.assertIsNotNone(D._METRIC_RESOLVER)

    def test_a_role_and_a_counter_are_answered(self):
        from sbs_utils.procedural.query import to_id
        from sbs_utils.procedural.sides import side_ensure
        from sbs_utils.procedural.spawn import player_spawn
        side_ensure("tsn")
        ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.assertFalse(D.dialogue_guard_ok("tsn", ship, None))
        D.dialogue_register_scenes(amd_section(amd_document(MISSION), "dialogue"))
        self.assertTrue(D.dialogue_guard_ok("tsn", ship, None))
        self.assertFalse(D.dialogue_guard_ok("learned >= 1", ship, None))
        D.dialogue_apply(ship, None, [("learn", "told_quill")])
        self.assertTrue(D.dialogue_guard_ok("learned >= 1", ship, None))


class AnOutcomeThatDidNothingIsSaidTests(unittest.TestCase):
    def test_the_drivers_sentence_reaches_the_runtime_log(self):
        from sbs_utils.procedural import quest_driver as QD
        heard = []

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        handler = _Listen()
        logging.getLogger("mast.runtime").addHandler(handler)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, handler)
        QD._quest_driver_log("nobody holds 'tag_hulkk', so `accepts tag_hulkk` did nothing")
        self.assertEqual(len([l for l in heard if "tag_hulkk" in l]), 1)


class AnAnswersWordsAreALiteralTests(unittest.TestCase):
    def test_curly_brackets_survive_one_format_pass(self):
        from sbs_utils.procedural.gui.hail_gui import _hail_text
        text = _hail_text("Call me {Captain}, DS 1.")
        self.assertIn("{{Captain}}", text)
        # What `gui_text` does with it: one format pass gives the words back.
        self.assertIn("{Captain}", eval('f"""' + text + '"""'))


if __name__ == "__main__":
    unittest.main()
