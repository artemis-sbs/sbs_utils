"""Content the mission never loads, and a key where the game wants a role.

Found by the lesson "Things quests point at". A mission's `story.mast` reads its `.amd`
one section at a time, by key. Everything below linted clean, ran with an empty log, and
put nothing in the game:

    ## [Places](places)                  the story asks for `landmarks`
    a landmark with no `Art:`            not placed
    a landmark with no `Loc:`            placed at 0, 0, 0, inside the station
    a landmark with no `Kind:`           made as a station, wearing that role
    Done when: reach lifeboat 500        `lifeboat` is the landmark's KEY; reach wants a ROLE
    wreck                                (alone on the fence's first line) a kind nobody knows

    python -m unittest tests.test_amd_lint_mission_reads
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_lint import amd_lint

STORY = '''shared MISSION_DOC = None
crew_load_amd("mission.amd")

@map/amd_sample "AMD Sample"
    shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"), data_parser=amd_mission_data)
    lifeforms_spawn(amd_section(MISSION_DOC, "characters"))
    dialogue_register_scenes(amd_section(MISSION_DOC, "dialogue"))
    landmarks_spawn(amd_section(MISSION_DOC, "landmarks"))
    quest_grant_amd(SHARED, amd_section(MISSION_DOC, "quests"))
    science_define_scan_amd(amd_section(MISSION_DOC, "scans"))
    relics_spawn(get_mission_dir_filename("mission.amd"))
    ->END
'''

MISSION = """# [Sample Mission](sample_mission)

## [Quests](quests)

### [Find the Lifeboat](boat)
---
Scope: shared
Starts when: at once
Done when: reach lifeboat 500
---
Go and look.

## [Landmarks](landmarks)

### [The Lifeboat](lifeboat)
---
Kind: wreck
Roles: lifeboat
Art: wreck
Loc: 6000, 0, 6000
---
Adrift.

## [Scans](scans)

### [Lifeboat](lifeboat_scan)
---
Scan of: lifeboat
Tab: scan
---
% One lifeboat, cold.

## [The Watch](watch)
---
crew
Ship: Artemis
---

### [Chief Okoro](okoro)
---
Console: engineering
---
"""

CODES = ("landmark-record-level", "section-not-loaded", "landmark-no-art", "landmark-no-loc", "landmark-bad-loc",
         "landmark-no-kind", "role-is-a-key", "unknown-kind-line")


def _found(text, story=STORY, name="mission.amd"):
    return [f for f in amd_lint(file_path=name, content=text, mast_sources=[story],
                                cross_file=False) if f.code in CODES]


def _codes(text, **kw):
    return [f.code for f in _found(text, **kw)]


def _swap(old, new, text=MISSION):
    assert text.count(old) == 1, old
    return text.replace(old, new)


class TheLessonsFileIsCleanTests(unittest.TestCase):
    def test_nothing_is_reported(self):
        self.assertEqual(_codes(MISSION), [])


class ASectionNothingReadsTests(unittest.TestCase):
    def test_a_renamed_key(self):
        found = _found(_swap("## [Landmarks](landmarks)", "## [Places](places)"))
        mine = [f for f in found if f.code == "section-not-loaded"]
        self.assertEqual(len(mine), 1)
        self.assertIn("landmarks", mine[0].message)        # says what the story asks for

    def test_a_story_with_no_line_for_it(self):
        story = STORY.replace('    landmarks_spawn(amd_section(MISSION_DOC, "landmarks"))\n', "")
        self.assertIn("section-not-loaded", _codes(MISSION, story=story))

    def test_a_crew_roster_is_read_by_its_own_loader(self):
        self.assertNotIn("section-not-loaded", _codes(MISSION))
        story = STORY.replace('crew_load_amd("mission.amd")\n', "")
        self.assertIn("section-not-loaded", _codes(MISSION, story=story))

    def test_a_ruin_is_read_by_its_own_loader(self):
        ruin = MISSION + "\n## [Ruins](ruins)\n\n### [The Hollow](hollow)\n---\nLoc: 0, 0, 20000\n---\n"
        self.assertNotIn("section-not-loaded", _codes(ruin))

    def test_a_file_the_story_does_not_name_is_left_alone(self):
        text = _swap("## [Landmarks](landmarks)", "## [Places](places)")
        self.assertEqual(_codes(text, name="universe.amd"), [])

    def test_a_section_read_through_a_variable_silences_the_rule(self):
        story = STORY + "    quest_grant_amd(SHARED, amd_section(MISSION_DOC, which))\n"
        text = _swap("## [Landmarks](landmarks)", "## [Places](places)")
        self.assertNotIn("section-not-loaded", _codes(text, story=story))


class ALandmarkTheSpawnerWillNotPlaceTests(unittest.TestCase):
    def test_no_art(self):
        self.assertIn("landmark-no-art", _codes(_swap("Art: wreck\n", "")))

    def test_no_loc(self):
        self.assertIn("landmark-no-loc", _codes(_swap("Loc: 6000, 0, 6000\n", "")))

    def test_two_numbers(self):
        self.assertIn("landmark-bad-loc",
                      _codes(_swap("Loc: 6000, 0, 6000", "Loc: 6000, 6000")))

    def test_no_kind(self):
        self.assertIn("landmark-no-kind", _codes(_swap("Kind: wreck\n", "")))

    def test_a_landmark_nested_under_another(self):
        second = ("\n#### [Buoy 7](buoy)\n---\nKind: wreck\nRoles: buoy\nArt: wreck\n"
                  "Loc: 1000, 0, 1000\n---\nA buoy.\n")
        text = MISSION.replace("Adrift.\n", "Adrift.\n" + second)
        self.assertIn("landmark-record-level", _codes(text))

    def test_a_zone_needs_neither(self):
        text = _swap("Kind: wreck\nRoles: lifeboat\nArt: wreck\nLoc: 6000, 0, 6000",
                     "Kind: point\nRoles: lifeboat")
        self.assertEqual(_codes(text), [])

    def test_a_mission_that_places_its_own_is_left_alone(self):
        story = STORY.replace("landmarks_spawn(amd_section", "my_places(amd_section")
        self.assertEqual(_codes(_swap("Art: wreck\n", ""), story=story), [])


class AKeyWhereTheGameWantsARoleTests(unittest.TestCase):
    def test_reach_a_landmark_with_no_roles(self):
        found = [f for f in _found(_swap("Roles: lifeboat\n", "")) if f.code == "role-is-a-key"]
        self.assertEqual(len(found), 2)                    # the quest and the scan
        self.assertIn("Roles: lifeboat", found[0].message)

    def test_a_role_that_differs_from_the_key(self):
        text = _swap("Roles: lifeboat\n", "Roles: boat\n")
        self.assertIn("role-is-a-key", _codes(text))

    def test_a_number_is_not_a_role(self):
        text = _swap("Done when: reach lifeboat 500", "Done when: reach 6, 4")
        self.assertEqual(_codes(text), [])


class ARoleNothingWearsTests(unittest.TestCase):
    """`reach lifebaot 500` is a step that cannot finish; `Scan of: derelect` is a tab
    that never appears. Judged against the words in the story's own strings, the
    `Roles:` lines in the file and the roles the engine hands out."""

    STORY = STORY.replace(
        "    ->END\n",
        '    npc_spawn(0, 0, 9000, "Hulk", "tsn, derelict", "tsn_warpster", "behav_npcship")\n'
        "    ->END\n")
    CODES = ("role-nothing-wears", "scan-of-many", "duplicate-scan", "scan-record-level")

    def found(self, text):
        return [f for f in amd_lint(file_path="mission.amd", content=text,
                                    mast_sources=[self.STORY], cross_file=False)
                if f.code in self.CODES]

    def codes(self, text):
        return [f.code for f in self.found(text)]

    def test_the_lessons_file_is_quiet(self):
        self.assertEqual(self.codes(MISSION), [])

    def test_a_misspelled_role_after_reach(self):
        got = self.found(_swap("Done when: reach lifeboat 500", "Done when: reach lifebaot 500"))
        self.assertEqual([f.code for f in got], ["role-nothing-wears"])
        self.assertIn("lifebaot", got[0].message)

    def test_a_misspelled_scan_of(self):
        self.assertIn("role-nothing-wears",
                      self.codes(_swap("Scan of: lifeboat", "Scan of: lifebote")))

    def test_a_role_from_the_story_is_known(self):
        text = _swap("Done when: reach lifeboat 500", "Done when: reach derelict 500")
        self.assertEqual(self.codes(text), [])

    def test_a_plural_the_game_makes_singular_is_known(self):
        text = _swap("Done when: reach lifeboat 500", "Done when: scan 2 derelicts")
        self.assertEqual(self.codes(text), [])

    def test_a_role_the_engine_hands_out_is_known(self):
        text = _swap("Done when: reach lifeboat 500", "Done when: reach station 1000")
        self.assertEqual(self.codes(text), [])

    def test_a_signal_or_a_time_is_not_a_role(self):
        for value in ("signal log_found", "10 minutes", "reach 6, 4"):
            text = _swap("Done when: reach lifeboat 500", "Done when: " + value)
            self.assertEqual(self.codes(text), [], value)

    def test_two_roles_in_one_scan_of(self):
        self.assertIn("scan-of-many",
                      self.codes(_swap("Scan of: lifeboat", "Scan of: lifeboat, derelict")))

    def test_two_records_for_one_role_and_tab(self):
        again = "### [Again](again_scan)\n---\nScan of: lifeboat\n---\n% Twice.\n\n"
        text = MISSION.replace("## [The Watch](watch)", again + "## [The Watch](watch)")
        self.assertIn("duplicate-scan", self.codes(text))

    def test_a_mission_on_an_addons_world_is_not_second_guessed(self):
        story = self.STORY.replace("landmarks_spawn(amd_section", "my_places(amd_section")
        text = _swap("Done when: reach lifeboat 500", "Done when: reach lifebaot 500")
        got = [f.code for f in amd_lint(file_path="mission.amd", content=text,
                                        mast_sources=[story], cross_file=False)
               if f.code == "role-nothing-wears"]
        self.assertEqual(got, [])


class ABareWordThatIsNotAKindTests(unittest.TestCase):
    def test_kind_written_without_its_label(self):
        found = _found(_swap("Kind: wreck\n", "wreck\n"))
        mine = [f for f in found if f.code == "unknown-kind-line"]
        self.assertEqual(len(mine), 1)
        self.assertIn("Kind: wreck", mine[0].message)

    def test_real_kind_words_are_quiet(self):
        for word in ("crew", "Arc", "Beat", "Job", "Quest", "Characters"):
            text = _swap("Scope: shared\n", word + "\nScope: shared\n")
            self.assertNotIn("unknown-kind-line", _codes(text), word)


if __name__ == "__main__":
    unittest.main()
