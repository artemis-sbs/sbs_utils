"""A side key that names no side.

Found by the lesson "Sides and factions". `Enemies: tsm`, `Enemies: tsn guild` and
`Side: braker` were lint clean, compiled, and left `mast.runtime.log` empty: the relation
was not made, the cutter was on no side, and the crew saw a contact that was `unknown`
for good. The game's only word was `Side not found`, in a log category nothing reads.

    python -m unittest tests.test_amd_lint_sides
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural.amd_lint import amd_lint

GOOD = """# [Mission](mission)

## [Sides](sides)

### [TSN](tsn)
---
Color: #07F
---
The crew's own.

### [The Breakers](breaker)
---
Color: #F80
Enemies: tsn, guild
---
Scavengers.

### [Harbor Guild](guild)
---
Color: #0C6
Allies: tsn
---
Pilots and tug crews.

## [Landmarks](landmarks)

### [Breaker Cutter](cutter)
---
Kind: ship
Art: pirate_strongbow
Loc: 3000, 0, 11000
Side: breaker
---
"""

STORY = ('shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"))\n'
         'sides_declare_amd(amd_section(MISSION_DOC, "sides"))\n'
         'landmarks_spawn(amd_section(MISSION_DOC, "landmarks"))\n')


def found(text, story=STORY):
    return [f for f in amd_lint(file_path="mission.amd", content=text, cross_file=False,
                                mast_sources=[story] if story else None)
            if f.code == "dangling-side"]


def swapped(old, new):
    assert GOOD.count(old) == 1, old
    return GOOD.replace(old, new)


class SideKeyLint(unittest.TestCase):
    def test_the_lesson_as_written_is_clean(self):
        self.assertEqual(found(GOOD), [])

    def test_a_side_that_is_not_there(self):
        got = found(swapped("Enemies: tsn, guild", "Enemies: tsm, guild"))
        self.assertEqual(len(got), 1)
        self.assertIn("`tsm`", got[0].message)
        self.assertIn("breaker, guild, tsn", got[0].message)

    def test_no_comma_between_two_sides(self):
        for value in ("tsn guild", "tsn and guild", "tsn; guild"):
            with self.subTest(value=value):
                got = found(swapped("Enemies: tsn, guild", "Enemies: " + value))
                self.assertEqual(len(got), 1)
                self.assertIn("comma", got[0].message)

    def test_allies_and_neutral_are_judged_too(self):
        self.assertEqual(len(found(swapped("Allies: tsn", "Allies: tsnn"))), 1)
        self.assertEqual(len(found(swapped("Allies: tsn", "Neutral: nobody_here"))), 1)

    def test_side_on_a_landmark(self):
        got = found(swapped("Side: breaker", "Side: braker"))
        self.assertEqual(len(got), 1)
        self.assertIn("`braker`", got[0].message)

    def test_capitals_and_the_stock_words_are_fine(self):
        for old, new in (("Enemies: tsn, guild", "Enemies: TSN, Guild"),
                         ("Enemies: tsn, guild", "Enemies: players"),
                         ("Enemies: tsn, guild", "Enemies: *"),
                         ("Allies: tsn", "Allies: civilians")):
            with self.subTest(new=new):
                self.assertEqual(found(swapped(old, new)), [])

    def test_a_side_the_story_makes_counts(self):
        """The template makes `tsn` in MAST, with no record in the file."""
        text = GOOD.replace("### [TSN](tsn)\n---\nColor: #07F\n---\nThe crew's own.\n\n", "")
        self.assertEqual(len(found(text)), 2)            # tsn is now nobody's, twice
        story = STORY + 'tsn = await prefab_spawn(prefab_side_generic, data={"key":"tsn"})\n'
        self.assertEqual(found(text, story), [])

    def test_a_file_with_no_sides_is_not_judged(self):
        text = GOOD.split("## [Sides](sides)")[0] + "## [Landmarks](landmarks)" + \
            GOOD.split("## [Landmarks](landmarks)")[1]
        self.assertEqual(found(text.replace("Side: breaker", "Side: anything")), [])


class TheGameSaysItToo(unittest.TestCase):
    def test_side_not_found_reaches_the_runtime_log_once(self):
        from cosmos_dev.mock import sbs
        from tests.reset_helper import reset_mock
        from sbs_utils.procedural import sides as S
        reset_mock(sbs)
        heard = []

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        handler = _Listen()
        logging.getLogger("mast.runtime").addHandler(handler)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, handler)
        S._missing_side_warned.discard("c21_no_such_side")
        self.addCleanup(S._missing_side_warned.discard, "c21_no_such_side")
        S.to_side_id("c21_no_such_side")
        S.to_side_id("c21_no_such_side")
        said = [line for line in heard if "c21_no_such_side" in line]
        self.assertEqual(len(said), 1, heard)
        self.assertIn("Side not found", said[0])


if __name__ == "__main__":
    unittest.main()
