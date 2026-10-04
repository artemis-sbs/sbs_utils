"""Lint for a quest that belongs to one person, and for two outcomes run together.

Found by the lesson "Personal quests". Every one of these was lint clean, ran clean, left
the log empty, and handed the quest to nobody (or never sent the signal that finishes it).

    python -m unittest tests.test_amd_lint_personal_quests
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_lint import amd_lint

GOOD = """# [Mission](mission)

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

## [Scenes](boarding)

### [The Airlock](airlock)
% Cold.

- [Read the name tags](airlock) if medical ; learn suits, signal names_read
- [Return to the ship]()

## [Side Stories](side_stories)

### [Six Names](six_names)
---
For: medical
Starts when: at once
Done when: signal names_read
---
Read the tags.
"""

STORY = ('shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"))\n'
         'boarding_visit(ship, SCENES, "airlock", '
         'stories=amd_section(MISSION_DOC, "side_stories"))\n')

MINE = ("outcome-run-together", "for-nobody", "for-shared", "for-not-started", "for-no-end",
        "for-nested", "story-no-for", "for-in-quests", "stories-not-handed-out")


def codes(text, story=STORY):
    found = amd_lint(file_path="mission.amd", content=text,
                     mast_sources=[story] if story else None, cross_file=False)
    return sorted(f.code for f in found if f.code in MINE)


def swapped(old, new):
    assert GOOD.count(old) == 1, old
    return GOOD.replace(old, new)


class PersonalQuestLint(unittest.TestCase):
    def test_the_lesson_as_written_is_clean(self):
        self.assertEqual(codes(GOOD), [])

    def test_two_outcomes_with_no_comma(self):
        for tail in ("learn suits signal names_read", "learn suits and signal names_read"):
            with self.subTest(tail=tail):
                text = swapped("learn suits, signal names_read", tail)
                self.assertEqual(codes(text), ["outcome-run-together"])
        found = amd_lint(file_path="mission.amd", cross_file=False, content=swapped(
            "learn suits, signal names_read", "learn suits signal names_read"))
        said = [f.message for f in found if f.code == "outcome-run-together"][0]
        self.assertIn("; learn suits, signal names_read", said)

    def test_separated_outcomes_and_a_last_word_that_is_a_verb_are_left_alone(self):
        for tail in ("learn suits ; signal names_read", "learn door open",
                     "check engineering 9 else airlock, learn suits"):
            with self.subTest(tail=tail):
                self.assertEqual(codes(swapped("learn suits, signal names_read", tail)), [])

    def test_for_a_word_nobody_answers_to(self):
        for who in ("medcal", "security", "science", "medical, engineering", "everyone"):
            with self.subTest(who=who):
                self.assertEqual(codes(swapped("For: medical", "For: " + who)),
                                 ["for-nobody"])

    def test_for_takes_a_job_a_key_a_name_or_the_end_of_a_name(self):
        for who in ("medical", "Medical", "hale", "Dr Ines Hale", "Ines Hale", "Hale"):
            with self.subTest(who=who):
                self.assertEqual(codes(swapped("For: medical", "For: " + who)), [])

    def test_a_seat_is_a_job_only_when_the_roster_gave_no_role(self):
        text = swapped("Console: science\nRoles: medical\n", "Console: science\n")
        self.assertEqual(codes(text.replace("For: medical", "For: science")), [])

    def test_no_roster_in_the_file_is_not_second_guessed(self):
        text = GOOD.split("## [The Watch](watch)")[0] + "## [Side Stories]" + \
            GOOD.split("## [Side Stories]")[1]
        self.assertEqual(codes(text.replace("For: medical", "For: anyone at all")), [])

    def test_shared_scope_with_for(self):
        self.assertEqual(codes(swapped("For: medical\n", "For: medical\nScope: shared\n")),
                         ["for-shared"])

    def test_never_started(self):
        self.assertEqual(codes(swapped("Starts when: at once\n", "")), ["for-not-started"])
        self.assertEqual(codes(swapped("Starts when: at once", "Starts when: accepted")),
                         ["for-not-started"])
        self.assertEqual(codes(swapped("Starts when: at once", "State: active")), [])

    def test_nothing_finishes_it(self):
        self.assertEqual(codes(swapped("Done when: signal names_read\n", "")), ["for-no-end"])

    def test_one_hash_too_many(self):
        text = GOOD + ("\n#### [A Cold Core](cold_core)\n---\nFor: engineering\n"
                       "Starts when: at once\nDone when: signal core_read\n---\nFind out.\n")
        self.assertEqual(codes(text), ["for-nested"])

    def test_one_hash_too_few_is_said_about_the_quest_not_about_the_file(self):
        text = GOOD.replace("### [Six Names](six_names)", "## [Six Names](six_names)")
        found = amd_lint(file_path="mission.amd", content=text, mast_sources=[STORY],
                         cross_file=False)
        mine = [f for f in found if f.code in MINE + ("for-section-level",)]
        self.assertEqual([f.code for f in mine], ["for-section-level"])
        self.assertIn("3 hashes", mine[0].message)

    def test_a_quest_in_the_section_with_no_for(self):
        text = GOOD + ("\n### [A Cold Core](cold_core)\n---\nStarts when: at once\n"
                       "Done when: signal core_read\n---\nFind out.\n")
        self.assertEqual(codes(text), ["story-no-for"])


class HandedOutLint(unittest.TestCase):
    """What only the mission's MAST can say: is the section handed to anybody."""

    def test_no_card_at_all(self):
        story = STORY.replace(', stories=amd_section(MISSION_DOC, "side_stories")', "")
        self.assertEqual(codes(GOOD, story), ["stories-not-handed-out"])

    def test_the_key_on_the_card_is_not_the_key_on_the_heading(self):
        self.assertEqual(codes(GOOD, STORY.replace('"side_stories"', '"side_story"')),
                         ["stories-not-handed-out"])

    def test_the_older_card_counts(self):
        story = STORY.split("boarding_visit")[0] + (
            'shared SIDE = amd_section(MISSION_DOC, "side_stories")\n'
            "//shared/signal/boarding_went_down\n    boarding_quests_grant(SIDE)\n")
        self.assertEqual(codes(GOOD, story), [])
        self.assertEqual(codes(GOOD, story.replace("amd_section", "relic_section")), [])

    def test_for_under_the_section_the_ship_is_given(self):
        # With the ship's own quests beside it: they have no `For:` and want none.
        ships = ("\n### [Close Inspection](close)\n---\nStarts when: at once\n"
                 "Done when: signal seen\n---\nLook.\n"
                 "\n### [Account for the Crew](account)\n---\nStarts when: at once\n"
                 "Done when: signal names_known\n---\nNames.\n")
        text = GOOD.replace("## [Side Stories](side_stories)", "## [Quests](quests)") + ships
        story = STORY.split("boarding_visit")[0] + \
            'quest_grant_amd(SHARED, amd_section(MISSION_DOC, "quests"))\n'
        self.assertEqual(codes(text, story), ["for-in-quests"])

    def test_a_file_the_story_does_not_name_is_left_alone(self):
        story = STORY.replace("mission.amd", "other.amd").replace(
            ', stories=amd_section(MISSION_DOC, "side_stories")', "")
        self.assertEqual(codes(GOOD, story), [])
        self.assertEqual(codes(GOOD, None), [])

    def test_section_not_loaded_is_not_said_as_well(self):
        story = STORY.replace(', stories=amd_section(MISSION_DOC, "side_stories")', "") + \
            'x = amd_section(MISSION_DOC, "boarding")\ncrew_declare_amd(MISSION_DOC)\n'
        found = amd_lint(file_path="mission.amd", content=GOOD, mast_sources=[story],
                         cross_file=False)
        mine = [f.code for f in found if "Side Stories" in f.message]
        self.assertEqual(mine, ["stories-not-handed-out"])


if __name__ == "__main__":
    unittest.main()
