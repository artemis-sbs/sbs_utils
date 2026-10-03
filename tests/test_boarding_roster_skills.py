"""A roster's `Skills:` reaches the person, with no second call and under any name.

Found by the lesson "Crew and skills". A crew roster may say

    ### [Dr Hale](hale)
    ---
    Console: science
    Roles: medical
    Skills: medical 4, science 3
    ---

The schema declared `Skills:`, lint accepted it, and the roster reader dropped it: the
only code that read the numbers was a separate call (`boarding_skills_from_amd`) that one
shipped mission made and the mission template did not. So in a new mission every person
was 2 at their job and 0 at everything else, a choice written `if skill science >= 3` was
never offered to anyone, and nothing said why.

And where the call WAS made, the numbers were filed under the person's display name - so
a player who had saved a name of their own kept the job and lost every number.

Everything here goes in the front door: a roster written as AMD, a console seated by
`crew_assign`, `boarding_visit`, then what that console is offered and how it rolls.

    python -m unittest tests.test_boarding_roster_skills
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd import amd_choice_label
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

ENG = 0x8000000000000002
SCI = 0x8000000000000003

MISSION = """# [Mission](mission)

## [The Watch](watch)
---
crew
Ship: Artemis
{names}---

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

## [Scenes](boarding)

### [The Bridge](bridge)
% Dark.

- [Pull the sensor record](bridge) if skill science >= 3 ; learn record
- [Return to the ship]()
"""


class RosterSkillsTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        crew.crew_clear()
        A.boarding_clear()
        C.boarding_checks_clear()
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        self.addCleanup(C.boarding_checks_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))

    def declare(self, names=""):
        text = MISSION.format(names=names)
        crew.crew_declare_amd(amd_document(text, data_parser=amd_crew_data))
        self.scenes = dialogue_scenes(amd_section(amd_document(text), "boarding"))

    def sit(self, client_id, console, **own):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        link(self.ship, "consoles", client_id)
        return crew.crew_assign(client_id, self.ship, console, **own)

    def go(self, *consoles):
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "bridge", title="T"))
        for client_id in consoles:
            self.assertIsNotNone(A.boarding_beam_down(client_id))

    def offered(self, client_id):
        return [amd_choice_label(c.get("label")) for c in A.boarding_choices(client_id)]

    def body(self, client_id):
        return A.boarding_me(client_id)

    def test_the_numbers_are_read_with_no_second_call(self):
        self.declare()
        self.sit(ENG, "engineering")
        self.sit(SCI, "science")
        self.go(ENG, SCI)
        self.assertEqual(C.boarding_skill(self.body(ENG), "engineering"), 4)
        self.assertEqual(C.boarding_skill(self.body(ENG), "science"), 1)
        self.assertEqual(C.boarding_skill(self.body(SCI), "science"), 3)
        self.assertEqual(C.boarding_skill(self.body(SCI), "medical"), 4)

    def test_a_skill_gate_is_offered_to_the_one_who_has_it(self):
        self.declare()
        self.sit(ENG, "engineering")
        self.sit(SCI, "science")
        self.go(ENG, SCI)
        self.assertIn("Pull the sensor record", self.offered(SCI))
        self.assertNotIn("Pull the sensor record", self.offered(ENG))

    def test_a_job_with_no_number_is_still_two(self):
        self.declare()
        self.sit(SCI, "science")
        self.go(SCI)
        self.assertEqual(C.boarding_skill(self.body(SCI), "engineering"), 0)
        # Hale's `Roles: medical` has a number; a job WITHOUT one is the fallback.
        C.boarding_skills_set(self.body(SCI), {})
        self.assertEqual(C.boarding_skill(self.body(SCI), "medical"), C.JOB_SKILL)

    def test_a_player_with_a_name_of_their_own_keeps_the_numbers(self):
        self.declare()
        post = self.sit(SCI, "science", own_name="Zed")
        self.assertEqual(post.name, "Zed")
        self.go(SCI)
        self.assertEqual(C.boarding_skill(self.body(SCI), "science"), 3)
        self.assertIn("Pull the sensor record", self.offered(SCI))


if __name__ == "__main__":
    unittest.main()
