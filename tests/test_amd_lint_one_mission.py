"""A mission is ONE thing, however many files it is written in.

Found by the author course, Classes 4, 5 and 6. Each of these was a warning on a
mission that works, and a lesson then had to teach "ignore this warning":

* an answer in `dialogue\\deepwell.amd` sends `; signal ledger_read` and a step in the
  universe file waits `Done when: signal ledger_read` - two `signal-no-route` and one
  `unfired-signal`, all false (Class 5 Lecture 9 ended on those three, Lecture 10 on
  nine);
* a ruin in a file of its own sends `<barrier>_opened` and `<ruin>_taken`, waited for in
  the universe file - two false `unfired-signal` (Class 5 Lecture 11);
* a ruin's own `## [Side Stories](side_stories)` is handed out by the `boarding` addon,
  and lint said `stories-not-handed-out` (Class 4 Lectures 6 and 10);
* a chapter with a `File:` line AND a record written under it was read "as a map" -
  five `unknown-field` (Class 5 Lecture 9);
* `Then: tern_ledger`, no verb, reveals the step - and the step was `never-revealed`.

And two that were clean and wrong: `#` in front of `relics_spawn(...)` still counted as
the line that reads the Relics section, and `section-not-loaded` listed six sections of
the nine the story reads.

    python -m unittest tests.test_amd_lint_one_mission
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural import amd_core
from sbs_utils.procedural.amd_lint import amd_lint


class _Mission(unittest.TestCase):
    """A mission folder on disk, linted the way `sbs lint` does it: every `.amd` in turn,
    with the story's text and every key in the mission handed in."""

    STORY = "# a story\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "MyUniverse")
        os.makedirs(self.root)
        self.write("story.json", '{"mastlib": []}\n')
        self.write("story.mast", self.STORY)

    def write(self, name, text):
        path = os.path.join(self.root, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def lint(self, extra_sources=()):
        amd, sources = [], []
        for folder, _dirs, names in os.walk(self.root):
            for name in sorted(names):
                path = os.path.join(folder, name)
                if name.endswith(".amd"):
                    amd.append(path)
                elif name.endswith((".mast", ".py")):
                    with open(path, encoding="utf-8") as f:
                        sources.append(f.read())
        sources += list(extra_sources)
        keys = set()
        for path in amd:
            keys |= amd_core.parse(None, file_path=path).keys
        out = {}
        for path in sorted(amd):
            rel = os.path.relpath(path, self.root).replace(os.sep, "/")
            out[rel] = amd_lint(file_path=path, mast_sources=sources, known_keys=keys)
        return out

    def codes(self, found=None, **kw):
        found = self.lint(**kw) if found is None else found
        return sorted((rel, f.code) for rel, fs in found.items() for f in fs)


# --- Class 5, Lecture 9: the dialogue moved out of the universe file ---------------------

UNIVERSE = """# [The Kestrel Verge](kestrel_verge)
---
Universe
---

## [Narrative](narrative)

### [The Tern](lead_tern)
---
Scope: shared
Starts when: at once
Done when: reach 1, -2
Then: reveal tern_ledger
---
The Tern never answered.

### [The Assay Ledger](tern_ledger)
---
Scope: shared
Starts when: revealed
Done when: signal ledger_read
Reward: 200 credits
---
Hail the Assay Office and ask.

## [Dialogue](dialogue)
---
File: dialogue/deepwell.amd
---
"""

DEEPWELL = """// What the Deepwell Assembly say.

# [Deepwell Hail](deepwell_hail)
---
Speaker: deepwell
When: comms
---
% Assay Office. Have your manifest ready.

- [Pay the search fee and ask about the Tern](deepwell_ledger) ; signal ledger_read
- [Demand the Tern's entry, now](deepwell_ledger) ; signal ledger_read
- [Sign off]()

# [The Ledger](deepwell_ledger)
---
Speaker: deepwell
---
% The Tern was logged out light.
- [Sign off]()
"""


class ASignalCrossesFiles(_Mission):
    def setUp(self):
        super().setUp()
        self.write("kestrel_verge.amd", UNIVERSE)
        self.write("dialogue/deepwell.amd", DEEPWELL)

    def signal_codes(self):
        return [c for c in self.codes() if c[1] in ("signal-no-route", "unfired-signal")]

    def test_THE_LESSONS_THREE_WARNINGS_ARE_GONE(self):
        self.assertEqual(self.signal_codes(), [])

    def test_the_neighbor_is_read_for_what_it_sends_and_waits_for(self):
        from sbs_utils.procedural.amd_lint import amd_mission_facts
        main = os.path.join(self.root, "kestrel_verge.amd")
        other = os.path.join(self.root, "dialogue", "deepwell.amd")
        self.assertEqual({s for f in amd_mission_facts(main) for s in f["sends"]},
                         {"ledger_read"})
        self.assertEqual({s for f in amd_mission_facts(other) for s in f["waits"]},
                         {"ledger_read"})

    def test_a_misspelled_wait_is_still_caught(self):
        self.write("kestrel_verge.amd",
                   UNIVERSE.replace("Done when: signal ledger_read",
                                    "Done when: signal ledger_red"))
        self.assertEqual(self.signal_codes(),
                         [("dialogue/deepwell.amd", "signal-no-route"),
                          ("dialogue/deepwell.amd", "signal-no-route"),
                          ("kestrel_verge.amd", "unfired-signal")])

    def test_a_signal_nothing_in_the_mission_waits_for_is_still_caught(self):
        self.write("dialogue/deepwell.amd",
                   DEEPWELL.replace("- [Sign off]()\n\n",
                                    "- [Sign off]() ; signal nobody_waits\n\n", 1))
        self.assertIn(("dialogue/deepwell.amd", "signal-no-route"), self.signal_codes())
        self.assertEqual(len(self.signal_codes()), 1)

    def test_a_loose_file_has_no_neighbors(self):
        """No `story.json` above it: nothing is read from beside it."""
        from sbs_utils.procedural.amd_lint import amd_mission_facts
        os.remove(os.path.join(self.root, "story.json"))
        os.remove(os.path.join(self.root, "story.mast"))
        self.assertEqual(amd_mission_facts(os.path.join(self.root, "kestrel_verge.amd")),
                         [])

    def test_a_name_with_no_file_behind_it_has_no_neighbors(self):
        from sbs_utils.procedural.amd_lint import amd_mission_facts
        self.assertEqual(amd_mission_facts(os.path.join(self.root, "not_there.amd")), [])


# --- Class 5, Lecture 11: a ruin in a file of its own ------------------------------------

HOLLOW = """# [The Hollow](hollow_file)

## [Relics](relics)

### [The Hollow](hollow)
---
Walls: rock
Loc: 40000, 0, 40000
---
An old place.

### [The Nave](nave)
---
Relic: hollow
Chamber: 0, 0, 0, 900
---

### [The Fallen Slab](slab)
---
Relic: hollow
Barrier: 300, 0, -110, 320
---

### [The Niche](niche)
---
Relic: hollow
Point: 100, 0, 100
Roles: niche, relic_piece
Item: stone_bowl
---

## [Items](items)

### [The Stone Bowl](stone_bowl)
---
Art: container_1a
---
A bowl.
"""

RUIN_STEPS = """# [The Kestrel Verge](kestrel_verge)
---
Universe
---

## [Narrative](narrative)

### [Cut Through](hollow_cut)
---
Scope: shared
Starts when: at once
Done when: signal slab_opened
Then: reveal hollow_bowl
---
Somebody has to suit up and cut it.

### [What the Hollow Kept](hollow_bowl)
---
Scope: shared
Starts when: revealed
Done when: signal hollow_taken
---
Bring it aboard.
"""


class ARuinInItsOwnFile(_Mission):
    def setUp(self):
        super().setUp()
        self.write("kestrel_verge.amd", RUIN_STEPS)
        self.write("hollow.amd", HOLLOW)

    def test_WHAT_THE_RUIN_SENDS_BY_ITSELF_ANSWERS_THE_STORY(self):
        self.assertEqual([c for c in self.codes() if c[1] == "unfired-signal"], [])

    def test_the_reverse_a_ruin_part_waits_for_what_an_answer_sends(self):
        self.write("hollow.amd", HOLLOW.replace(
            "Point: 100, 0, 100\n", "Point: 100, 0, 100\nStarts when: signal niche_open\n"))
        self.write("kestrel_verge.amd", RUIN_STEPS + """
## [Dialogue](dialogue)

### [Relay](relay_hail)
---
Speaker: relay
When: comms
---
% Go ahead.
- [Open the niche.]() ; signal niche_open
""")
        self.assertEqual([c for c in self.codes() if c[1] == "signal-no-route"], [])

    def test_a_misspelled_ruin_signal_is_still_caught(self):
        self.write("kestrel_verge.amd",
                   RUIN_STEPS.replace("signal hollow_taken", "signal hollow_taked"))
        self.assertEqual([c for c in self.codes() if c[1] == "unfired-signal"],
                         [("kestrel_verge.amd", "unfired-signal")])


# --- Class 4, Lectures 6 and 10: a ruin's own Side Stories --------------------------------

RUIN_MISSION = """# [The Hollow](mission)

## [Relics](relics)

### [The Hollow](hollow)
---
Walls: rock
Loc: 40000, 0, 40000
---

### [The Nave](nave)
---
Relic: hollow
Chamber: 0, 0, 0, 900
---

## [Dialogue](dialogue)

### [The Cairn](cairn_look)
---
Speaker: rook
---
% Forty-one stones.
- [Log it.]() ; signal count_matched

// ---- Side stories. A small story for one member of the crew who goes inside.
## [Side Stories](side_stories)

### [The Tally](the_tally)
---
For: comms
Starts when: at once
Objective: Find out what the tally on the altar was counting
Done when: signal count_matched
Reward: 80 credits
---
Somebody cut marks into the rim of the altar, in sets of five.
"""

RUIN_STORY = ('shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"))\n'
              'dialogue_register_scenes(amd_section(MISSION_DOC, "dialogue"))\n'
              'relics_spawn(get_mission_dir_filename("mission.amd"))\n')
# What a whole-mission lint is handed from the packaged `boarding` addon: its route lines.
EVA_ROUTES = "//shared/signal/relic_built\n//shared/signal/eva_went_out\n//shared/signal/eva_place_scene\n"


class ARuinsOwnSideStories(_Mission):
    STORY = RUIN_STORY

    def setUp(self):
        super().setUp()
        self.write("mission.amd", RUIN_MISSION)

    def test_THE_ADDON_HANDS_THEM_OUT_SO_NOTHING_IS_SAID(self):
        self.assertNotIn(("mission.amd", "stories-not-handed-out"),
                         self.codes(extra_sources=[EVA_ROUTES]))

    def test_without_the_addon_nothing_does_and_lint_still_says_so(self):
        self.assertIn(("mission.amd", "stories-not-handed-out"), self.codes())

    def test_a_route_that_is_only_a_note_is_not_a_route(self):
        self.assertIn(("mission.amd", "stories-not-handed-out"),
                      self.codes(extra_sources=["# //shared/signal/eva_went_out\n"]))

    def test_a_file_with_no_ruin_is_still_told(self):
        """The same section in a boarding mission needs `stories=`: no ruin, no addon."""
        text = RUIN_MISSION[:RUIN_MISSION.index("## [Relics]")] + \
            RUIN_MISSION[RUIN_MISSION.index("## [Dialogue]"):]
        self.write("mission.amd", text)
        self.assertIn(("mission.amd", "stories-not-handed-out"),
                      self.codes(extra_sources=[EVA_ROUTES]))

    def test_a_story_with_no_For_in_a_ruins_side_stories_is_nobodys(self):
        self.write("mission.amd", RUIN_MISSION.replace("For: comms\n", ""))
        found = self.lint(extra_sources=[EVA_ROUTES])
        got = [f for f in found["mission.amd"] if f.code == "story-no-for"]
        self.assertEqual(len(got), 1)
        self.assertIn("`The Tally`", got[0].message)
        self.assertIn("handed to nobody", got[0].message)


# --- Class 5, Lecture 10: a site's own Side Stories ----------------------------------------

SITE_UNIVERSE = """# [The Kestrel Verge](kestrel_verge)
---
Universe
---

## [Landmarks](landmarks)

### [Tally Yard](tally_station)
---
At: 0, 0
Kind: station
Site: tally_yard
---
A counting yard.
"""

SITE_FILE = """# [The Tally Yard](tally_yard_site)

## [Scenes](boarding)

### [The Gate](yard_gate)
% A chain across the gate.
- [Count the stacks](yard_gate) ; signal stacks_counted
- [Beam back up]()

## [Side Stories](side_stories)

### [Count the Stacks](count_stacks)
---
For: weapons
Starts when: at once
Done when: signal stacks_counted
Reward: 60 credits
---
Somebody should count them.
"""


class ASitesOwnSideStories(_Mission):
    def setUp(self):
        super().setUp()
        self.write("kestrel_verge.amd", SITE_UNIVERSE)

    def stories(self, text):
        self.write("tally_yard.amd", text)
        return [f for f in self.lint()["tally_yard.amd"]
                if f.code in ("story-no-for", "stories-not-handed-out")]

    def test_the_lessons_site_is_clean(self):
        self.assertEqual(self.stories(SITE_FILE), [])

    def test_A_STORY_WITH_NO_For_IS_HANDED_TO_NOBODY(self):
        """The universe gives a site's `side_stories` to the visit, one person each: a
        story with no `For:` is skipped (`boarding_quests_grant`), not shared."""
        got = self.stories(SITE_FILE.replace("For: weapons\n", ""))
        self.assertEqual([f.code for f in got], ["story-no-for"])
        self.assertIn("`Count the Stacks`", got[0].message)

    def test_the_same_file_that_no_landmark_names_is_not_a_site(self):
        self.write("kestrel_verge.amd", SITE_UNIVERSE.replace("Site: tally_yard\n", ""))
        self.assertEqual(self.stories(SITE_FILE.replace("For: weapons\n", "")), [])

    def test_what_the_game_does_with_it(self):
        """The claim, asked of the library: no `For:`, no grant."""
        from sbs_utils.procedural.boarding_quests import boarding_quests_grant
        section = {"children": [{"key": "count_stacks", "data": {"on_signal": {}}}]}
        self.assertEqual(boarding_quests_grant(section, team=[]), {})


# --- Class 4: the loader line with a `#` in front, and what the story reads --------------

class TheLineThatReadsTheSection(_Mission):
    STORY = RUIN_STORY

    def setUp(self):
        super().setUp()
        self.write("mission.amd", RUIN_MISSION.replace("For: comms\n", "For: comms\n"))

    def not_loaded(self, **kw):
        found = self.lint(**kw)
        return [f for f in found["mission.amd"] if f.code == "section-not-loaded"]

    def test_the_working_line_reads_the_relics_section(self):
        self.assertEqual(self.not_loaded(extra_sources=[EVA_ROUTES]), [])

    def test_A_HASH_IN_FRONT_OF_THE_LINE_TAKES_THE_RUIN_OUT(self):
        self.write("story.mast", RUIN_STORY.replace("relics_spawn(", "# relics_spawn("))
        got = self.not_loaded(extra_sources=[EVA_ROUTES])
        self.assertEqual(len(got), 1)
        self.assertIn("keyed `relics`", got[0].message)

    def test_THE_LIST_NAMES_EVERY_SECTION_THE_STORY_READS(self):
        """`relics_spawn` reads `relics`, `items` and `dialogue` by itself."""
        self.write("mission.amd", RUIN_MISSION + """
## [Things](things)

### [The Stone Bowl](stone_bowl)
---
Art: container_1a
---
A bowl.
""")
        got = self.not_loaded(extra_sources=[EVA_ROUTES])
        self.assertEqual(len(got), 1)
        self.assertIn("The story asks this file for: dialogue, items, relics.", got[0].message)


# --- Class 5, Lecture 9: a chapter with a `File:` line and a record under it ------------

CHAPTERS = """# [The Kestrel Verge](kestrel_verge)
---
Universe
---

## [Jobs](jobs)
---
File: jobs.amd
---

### [Ferry](ferry)
---
Done when: reach 1, -2
Reward: 90 credits
---
A short hop, for a short fee.

## [Dialogue](dialogue)
---
File: dialogue/deepwell.amd
---

### [Relay](relay_hail)
---
Speaker: relay
When: comms
---
% Go ahead.
- [Sign off]()
"""


class AChapterWithAFileLineAndARecord(_Mission):
    def setUp(self):
        super().setUp()
        self.write("kestrel_verge.amd", CHAPTERS)
        self.write("jobs.amd", "# [Patrol](patrol)\n---\nDone when: destroy 2 raider\n---\nx\n")
        self.write("dialogue/deepwell.amd", DEEPWELL)

    def test_NO_FIELD_IS_READ_AS_A_MAPS(self):
        self.assertEqual([c for c in self.codes() if c[1] == "unknown-field"], [])

    def test_the_records_under_the_chapter_are_what_the_chapter_holds(self):
        doc = amd_core.parse(CHAPTERS)
        kinds = {n.key: n.kind for n in doc.nodes}
        self.assertEqual(kinds["jobs"], "quest")
        self.assertEqual(kinds["ferry"], "quest")
        self.assertEqual(kinds["dialogue"], "dialogue")
        self.assertEqual(kinds["relay_hail"], "dialogue")
        self.assertEqual(kinds["kestrel_verge"], "map")

    def test_THE_GAME_READS_THE_SAME_KINDS(self):
        """Two readers, one grammar (`amd_schema.amd_resolve_kind_chain`)."""
        from sbs_utils.procedural.amd_doc import amd_document, amd_section
        doc = amd_document(CHAPTERS)
        jobs = amd_section(doc, "jobs")
        self.assertEqual(jobs.get("kind"), "quest")
        self.assertEqual(jobs["children"][0].get("kind"), "quest")
        self.assertEqual(jobs["data"].get("file"), "jobs.amd")
        self.assertEqual(amd_section(doc, "dialogue")["children"][0].get("kind"), "dialogue")

    def test_Files_WITH_AN_S_IS_THE_SAME_LINE(self):
        """`Files: a.amd, b.amd` works, and drew "Did you mean `File`?"."""
        self.write("kestrel_verge.amd", CHAPTERS.replace("File: jobs.amd", "Files: jobs.amd"))
        self.assertEqual([c for c in self.codes() if c[1] == "unknown-field"], [])

    def test_a_misspelled_field_under_the_chapter_is_now_judged_as_a_quests(self):
        self.write("kestrel_verge.amd", CHAPTERS.replace("Reward: 90", "Rewrad: 90"))
        found = self.lint()
        got = [f for f in found["kestrel_verge.amd"] if f.code == "unknown-field"]
        self.assertEqual(len(got), 1)
        self.assertIn("quest", got[0].message)
        self.assertIn("Reward", got[0].message)

    def test_a_record_keyed_like_a_section_is_not_taken_for_a_chapter(self):
        """Only a fence that names a `File:` makes a chapter of a record."""
        doc = amd_core.parse("""# [Crew](artemis_crew)
---
crew
---

## [The Scan Officer](scan)
---
Console: science
---
""")
        self.assertEqual({n.key: n.kind for n in doc.nodes}["scan"], "crew")


# --- `Then:` with no verb, and an answer's `; reveal` -------------------------------------

BARE_THEN = """# [Mission](mission)

## [Quests](quests)

### [The Tern](lead_tern)
---
Starts when: at once
Done when: reach 1, -2
Then: tern_ledger
---
x

### [The Assay Ledger](tern_ledger)
---
Starts when: revealed
Done when: reach 3, 1
---
x
"""


class WhatRevealsAStep(_Mission):
    def never(self, text):
        self.write("mission.amd", text)
        return [f for f in self.lint()["mission.amd"] if f.code == "never-revealed"]

    def test_A_THEN_WITH_NO_VERB_IS_A_REVEAL(self):
        self.assertEqual(self.never(BARE_THEN), [])

    def test_with_the_verb_it_was_always_fine(self):
        self.assertEqual(self.never(BARE_THEN.replace("Then: tern_ledger",
                                                      "Then: reveal tern_ledger")), [])

    def test_with_the_line_gone_it_is_never_revealed(self):
        got = self.never(BARE_THEN.replace("Then: tern_ledger\n", ""))
        self.assertEqual(len(got), 1)

    def test_AN_ANSWERS_REVEAL_REVEALS_NO_STEP(self):
        """`reveal` after an answer shows a thing on the ground. It starts no quest."""
        text = BARE_THEN.replace("Then: tern_ledger\n", "") + """
## [Dialogue](dialogue)

### [Relay](relay_hail)
---
Speaker: relay
When: comms
---
% Go ahead.
- [Ask what comes next](relay_hail) ; reveal tern_ledger
"""
        self.write("mission.amd", text)
        codes = [f.code for f in self.lint()["mission.amd"]]
        self.assertIn("never-revealed", codes)
        self.assertIn("outcome-quest-verb", codes)

    def test_an_answer_that_ACCEPTS_it_does_start_it(self):
        text = BARE_THEN.replace("Then: tern_ledger\n", "") + """
## [Dialogue](dialogue)

### [Relay](relay_hail)
---
Speaker: relay
When: comms
---
% Go ahead.
- [Ask what comes next](relay_hail) ; accepts tern_ledger
"""
        self.assertEqual(self.never(text), [])


if __name__ == "__main__":
    unittest.main()
