"""Skill numbers, skill gates and skill checks: the near misses that were silent.

Found by the lesson "Crew and skills". A writer gives the crew skills, gates a choice on
one and rolls against another - and each of those has a spelling that is read as
something else, with lint clean and no line in any log:

    Skills: medical 4 science 3          one skill, called "medical 4 science"
    - [..](..) if skill sience >= 3      never offered
    - [..](..) if science >= 3           a JOB is 1 or 0: never offered
    - [..](..) ; check engineering nine  nothing is rolled; it always works
    - [..](..) ; check engineering 9 else core_ded      a failed roll ends the visit

    python -m unittest tests.test_amd_lint_skills
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd import amd_choice
from sbs_utils.procedural.amd_lint import amd_lint

GOOD = """# [Mission](mission)

## [The Watch](watch)
---
crew
Ship: Artemis
Names: locked
---

### [Chief Okoro](okoro)
---
Console: engineering
Roles: engineering
Skills: engineering 4, science 1
---

### [Dr Hale](hale)
---
Console: science
Roles: medical
Skills: medical 4, science 3
---

## [The Hulk](boarding)

### [The Bridge](bridge)
% Dark, and cold.

- [Pull the sensor record](bridge) if skill science >= 3 ; learn sensors
- [Go below](reactor)

### [The Reactor](reactor)
% The core is asleep.

- [Try to wake the core](core_wakes) ; check engineering 9 else core_dead, learn lockout
- [Go back](bridge)

### [The Core Wakes](core_wakes)
% The board lights.

- [Go back](bridge)

### [Nothing](core_dead)
% Nothing.

- [Go back](reactor)
"""

GATE = "- [Pull the sensor record](bridge) if skill science >= 3 ; learn sensors"
CHECK = "- [Try to wake the core](core_wakes) ; check engineering 9 else core_dead, learn lockout"
HALE = "Skills: medical 4, science 3"

SKILL_CODES = ("skills-shape", "skills-on-roster", "repeated-skills", "crew-member-level",
               "skill-gate-shape", "unknown-skill", "job-gate-never", "check-shape",
               "check-else-missing")


def _codes(text):
    return [f.code for f in amd_lint(content=text, cross_file=False)
            if f.code in SKILL_CODES]


def _swap(old, new, text=GOOD):
    assert text.count(old) == 1, old
    return text.replace(old, new)


class TheLessonsFileIsCleanTests(unittest.TestCase):
    def test_nothing_is_reported(self):
        self.assertEqual([f.code for f in amd_lint(content=GOOD, cross_file=False)], [])

    def test_capitals_do_not_matter(self):
        text = _swap(HALE, "Skills: Medical 4, Science 3")
        text = _swap(GATE, GATE.replace("skill science", "skill Science"), text)
        self.assertEqual(_codes(text), [])

    def test_a_file_with_no_roster_is_not_second_guessed(self):
        rooms = GOOD[GOOD.index("## [The Hulk]"):]
        self.assertEqual(_codes("# [Mission](mission)\n\n" + rooms), [])


class SkillsLineTests(unittest.TestCase):
    def test_every_dropped_spelling(self):
        for bad in ("medical 4 science 3", "medical: 4, science 3", "medical=4, science 3",
                    "4 medical, science 3", "medical 4, science three",
                    "medical 4 and science 3"):
            self.assertIn("skills-shape", _codes(_swap(HALE, "Skills: " + bad)), bad)

    def test_two_lines_on_one_person(self):
        text = _swap(HALE, "Skills: medical 4\nSkills: science 3")
        self.assertIn("repeated-skills", _codes(text))

    def test_skills_on_the_roster_itself(self):
        text = _swap("Names: locked\n", "Names: locked\nSkills: science 3\n")
        self.assertIn("skills-on-roster", _codes(text))


class TheRosterLosesAPersonTests(unittest.TestCase):
    def test_one_hash_too_many(self):
        found = [f for f in amd_lint(content=_swap("### [Dr Hale](hale)", "#### [Dr Hale](hale)"),
                                     cross_file=False) if f.code == "crew-member-level"]
        self.assertEqual(len(found), 1)
        self.assertIn("3 hashes", found[0].message)

    def test_one_hash_too_few(self):
        self.assertIn("crew-member-level",
                      _codes(_swap("### [Dr Hale](hale)", "## [Dr Hale](hale)")))


class GateTests(unittest.TestCase):
    def test_a_misspelled_skill(self):
        self.assertIn("unknown-skill",
                      _codes(_swap(GATE, GATE.replace("skill science", "skill sience"))))

    def test_the_word_skill_left_out(self):
        self.assertIn("job-gate-never",
                      _codes(_swap(GATE, GATE.replace("skill science", "science"))))

    def test_a_job_on_its_own_is_fine(self):
        text = _swap(GATE, "- [Pull the sensor record](bridge) if science ; learn sensors")
        self.assertEqual(_codes(text), [])

    def test_a_counter_is_not_a_job(self):
        text = _swap(GATE, "- [Pull the sensor record](bridge) if learned >= 2 ; learn sensors")
        self.assertEqual(_codes(text), [])

    def test_no_sign(self):
        self.assertIn("skill-gate-shape",
                      _codes(_swap(GATE, GATE.replace("science >= 3", "science 3"))))

    def test_skills_for_skill(self):
        self.assertIn("skill-gate-shape",
                      _codes(_swap(GATE, GATE.replace("skill science", "skills science"))))

    def test_no_skill_named(self):
        self.assertIn("skill-gate-shape",
                      _codes(_swap(GATE, GATE.replace("skill science", "skill"))))

    def test_a_gated_line(self):
        text = _swap("% Dark, and cold.", "% Dark, and cold.\n%{skill sience >= 3} You know this hull.")
        self.assertIn("unknown-skill", _codes(text))


class CheckTests(unittest.TestCase):
    def test_every_unreadable_shape(self):
        for bad in ("check engineering else core_dead", "check engineering nine else core_dead",
                    "check engineering >= 9 else core_dead", "check zero g 9 else core_dead",
                    "check engineering 9 core_dead"):
            text = _swap(CHECK, CHECK.replace("check engineering 9 else core_dead", bad))
            self.assertIn("check-shape", _codes(text), bad)

    def test_a_misspelled_skill(self):
        text = _swap(CHECK, CHECK.replace("check engineering", "check enginering"))
        self.assertIn("unknown-skill", _codes(text))

    def test_else_to_a_room_that_is_not_there(self):
        text = _swap(CHECK, CHECK.replace("else core_dead", "else core_ded"))
        self.assertIn("check-else-missing", _codes(text))

    def test_a_check_with_no_else_is_allowed(self):
        text = _swap(CHECK, CHECK.replace(" else core_dead", ""))
        self.assertEqual(_codes(text), [])


class ASecondSemicolonTests(unittest.TestCase):
    """`; check engineering 9 else held ; learn lockout` - the form the library's own
    comments show - swallowed the second `;` into the check as a word."""

    def test_it_separates_outcomes(self):
        ch = amd_choice("- [Try](core_wakes) ; check engineering 9 else core_dead ; learn lockout")
        self.assertEqual(ch["outcomes"], [("check", "engineering", "9", "else", "core_dead"),
                                          ("learn", "lockout")])

    def test_a_comma_still_does(self):
        ch = amd_choice("- [Try](core_wakes) ; check engineering 9 else core_dead, learn lockout")
        self.assertEqual(ch["outcomes"], [("check", "engineering", "9", "else", "core_dead"),
                                          ("learn", "lockout")])

    def test_lint_is_clean_for_it(self):
        text = _swap(CHECK, CHECK.replace(", learn lockout", " ; learn lockout"))
        self.assertEqual([f.code for f in amd_lint(content=text, cross_file=False)], [])


class AnUnreadableCheckSaysSoAtRuntimeTests(unittest.TestCase):
    def test_it_is_logged(self):
        from sbs_utils.procedural.boarding_checks import _check_outcome
        heard = []

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        handler = _Listen()
        logging.getLogger("mast.runtime").addHandler(handler)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, handler)
        self.assertIsNone(_check_outcome(0, None, ("engineering", "nine", "else", "core_dead")))
        self.assertEqual(len([l for l in heard if "check engineering nine" in l]), 1)


if __name__ == "__main__":
    unittest.main()
