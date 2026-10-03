"""`Names: locked` on a crew roster: the cast is worn, not chosen.

A script that writes its own cast wants that cast on the bridge. Until this field there
was no way to say so that held: `CREW_EDIT: enable: false` hides the picker's Edit button,
but the picker still reads the name, face and pick each player saved on their own machine
and hands them in as the strongest tier - so anyone who had ever typed a name kept it over
the script's.

The lock ignores what the player saved for the seats the roster fills, on the ships it
crews. It does not erase it: the next mission, and a seat this roster leaves empty, see it
exactly as before.

    python -m unittest tests.test_crew_names_locked
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

SCI = 0x8000000000000001
WEAP = 0x8000000000000002

ROSTER = """# [Mission](mission)

## [The Watch](watch)
---
crew
Ship: Artemis
{names}---
The bridge crew.

### [Dr Hale](hale)
---
Rank: Lieutenant
Console: science
Face: terran_male
Roles: medical
---

## [Thursday Night](thursday)
---
crew
By: person
---
Real people.

### [Doug](doug)
---
Rank: Captain
---
"""


class _Base(unittest.TestCase):
    NAMES = ""

    def setUp(self):
        reset_mock(sbs)
        crew.crew_clear()
        self.addCleanup(crew.crew_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        crew.crew_declare_amd(amd_document(ROSTER.format(names=self.NAMES),
                                           data_parser=amd_crew_data))
        for cid, console in ((SCI, "science"), (WEAP, "weapons")):
            GuiClient(cid)
            set_inventory_value(cid, "CONSOLE_TYPE", console)


class LockedTests(_Base):
    NAMES = "Names: locked\n"

    def test_the_roster_says_it_is_locked(self):
        self.assertTrue(crew.crew_roster_locked(crew.crew_roster("watch")))

    def test_a_saved_name_does_not_replace_the_cast(self):
        post = crew.crew_assign(SCI, self.ship, "science", own_name="Doug")
        self.assertEqual(post.name, "Dr Hale")
        self.assertEqual(get_inventory_value(SCI, "CREW_NAME", None), "Dr Hale")

    def test_a_saved_face_does_not_replace_the_cast(self):
        mine = "ter #fff 1 2 3;"
        post = crew.crew_assign(SCI, self.ship, "science", own_face=mine)
        self.assertNotEqual(post.face, mine)

    def test_a_saved_pick_from_another_roster_does_not_replace_the_cast(self):
        post = crew.crew_assign(SCI, self.ship, "science",
                                own_pick=crew.crew_pick_value("thursday", "doug"))
        self.assertEqual(post.name, "Dr Hale")

    def test_the_post_and_the_console_both_say_locked(self):
        post = crew.crew_assign(SCI, self.ship, "science", own_name="Doug")
        self.assertTrue(post.locked)
        self.assertTrue(get_inventory_value(SCI, "CREW_LOCKED", False))
        self.assertEqual(post.source, "ship")

    def test_the_preview_agrees_with_the_assignment(self):
        """The picker shows who you are ABOUT to be; it must be who you then are."""
        shown = crew.crew_preview_post(SCI, self.ship, "science", own_name="Doug")
        self.assertEqual(shown.name, "Dr Hale")
        self.assertTrue(shown.locked)

    def test_the_cast_keeps_its_roles_under_the_lock(self):
        crew.crew_assign(SCI, self.ship, "science", own_name="Doug")
        self.assertEqual(get_inventory_value(SCI, "CREW_ROLES", None), "medical")

    def test_a_seat_the_roster_leaves_empty_is_still_the_players(self):
        """There is no cast name there to protect."""
        post = crew.crew_assign(WEAP, self.ship, "weapons", own_name="Doug")
        self.assertEqual(post.name, "Doug")
        self.assertFalse(post.locked)
        self.assertFalse(get_inventory_value(WEAP, "CREW_LOCKED", True))


class EditableIsUnchangedTests(_Base):
    """No `Names:` line, and `Names: editable`, are both what a roster always did."""

    def test_no_names_line_is_not_locked(self):
        self.assertFalse(crew.crew_roster_locked(crew.crew_roster("watch")))

    def test_a_saved_name_still_wins(self):
        post = crew.crew_assign(SCI, self.ship, "science", own_name="Doug")
        self.assertEqual(post.name, "Doug")
        self.assertEqual(post.source, "own")
        self.assertFalse(post.locked)

    def test_a_saved_pick_still_wins(self):
        post = crew.crew_assign(SCI, self.ship, "science",
                                own_pick=crew.crew_pick_value("thursday", "doug"))
        self.assertEqual(post.name, "Doug")

    def test_nobody_saved_anything_so_the_cast_answers(self):
        self.assertEqual(crew.crew_assign(SCI, self.ship, "science").name, "Dr Hale")


class EditableSpelledOutTests(EditableIsUnchangedTests):
    NAMES = "Names: editable\n"


class LintKnowsTheFieldTests(unittest.TestCase):
    def codes(self, names):
        return [f.code for f in amd_lint(content=ROSTER.format(names=names))]

    def test_locked_and_editable_are_clean(self):
        for value in ("Names: locked\n", "Names: editable\n"):
            got = self.codes(value)
            self.assertNotIn("unknown-field", got, value)
            self.assertNotIn("unknown-enum-value", got, value)

    def test_a_typo_is_flagged_rather_than_silently_editable(self):
        self.assertIn("unknown-enum-value", self.codes("Names: lokced\n"))


if __name__ == "__main__":
    unittest.main()
