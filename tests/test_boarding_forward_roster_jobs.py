"""A job the roster names is a job, whether or not anyone is sitting in that seat.

A crew party forwards a choice nobody present is qualified for to one console, so a short
crew still reaches every reading. "Is this guard a job" was answered from the stock words
and from the bodies in the party - and a body exists only for a console somebody is at.

So with one player at Engineering:

    - [Read the tags](suits) if medical ; learn suits               forwarded (stock word)
    - [Count the stores](stores) if quartermaster ; learn stores    never offered

The roster said `Roles: quartermaster` in so many words. Found by the third boarding
lesson, whose exercise is "give your third crew member a job of your choosing".

Everything here goes in the front door: a roster written as AMD, a console seated by
`crew_assign`, `boarding_visit`, then the choices that console is offered.

    python -m unittest tests.test_boarding_forward_roster_jobs
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd import amd_choice_label
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

ENG = 0x8000000000000002
HELM = 0x8000000000000003

MISSION = """# [Mission](mission)

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

### [Dr Hale](hale)
---
Console: science
Roles: medical
---

### [Mr Pell](pell)
---
Console: helm
Roles: quartermaster
---

## [Scenes](boarding)

### [The Airlock](airlock)
% Cold.

- [Read the tags](airlock) if medical ; learn suits
- [Count the stores](airlock) if quartermaster ; learn stores
- [Force the hatch](airlock) if briefed
- [Return to the ship]()
"""


class RosterJobsAreForwardedTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        crew.crew_clear()
        A.boarding_clear()
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        crew.crew_declare_amd(amd_document(MISSION, data_parser=amd_crew_data))
        self.scenes = dialogue_scenes(amd_section(amd_document(MISSION), "boarding"))

    def sit(self, client_id, console):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        link(self.ship, "consoles", client_id)
        return crew.crew_assign(client_id, self.ship, console)

    def offered(self, client_id):
        return {amd_choice_label(c.get("label")): getattr(c, "forwarded", None)
                for c in A.boarding_choices(client_id)}

    def go(self, *consoles):
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "airlock", title="T"))
        for client_id in consoles:
            self.assertIsNotNone(A.boarding_beam_down(client_id))

    def test_the_fixture_seats_the_engineer(self):
        self.assertEqual(self.sit(ENG, "engineering").name, "Chief Okoro")

    def test_a_stock_job_was_always_forwarded(self):
        self.sit(ENG, "engineering")
        self.go(ENG)
        self.assertEqual(self.offered(ENG).get("Read the tags"), "medical")

    def test_a_job_the_roster_names_is_forwarded_too(self):
        self.sit(ENG, "engineering")
        self.go(ENG)
        self.assertEqual(self.offered(ENG).get("Count the stores"), "quartermaster")

    def test_a_word_that_is_not_a_job_is_still_never_forwarded(self):
        """`briefed` has the shape of a job and is the story's own lock. Handing it over
        because nobody qualifies would give away the ending."""
        self.sit(ENG, "engineering")
        self.go(ENG)
        self.assertNotIn("Force the hatch", self.offered(ENG))

    def test_the_holder_gets_it_unforwarded_when_they_are_there(self):
        self.sit(ENG, "engineering")
        self.sit(HELM, "helm")
        self.go(ENG, HELM)
        self.assertIn("Count the stores", self.offered(HELM))
        self.assertIsNone(self.offered(HELM)["Count the stores"])
        self.assertNotIn("Count the stores", self.offered(ENG))

    def test_a_cast_party_is_deliberate_and_takes_nothing_from_the_roster(self):
        """A party a mission CASTS is three named people and no more. Its gaps are the
        mission saying something, so the roster does not fill them."""
        self.sit(ENG, "engineering")
        cast = [lifeform_spawn("Sgt Ruiz", "terran_male", "boarding, security")]
        self.assertIsNotNone(
            A.boarding_visit(self.ship, self.scenes, "airlock", title="T", cast=cast))
        self.assertNotIn("quartermaster", A.boarding_job_vocabulary())


if __name__ == "__main__":
    unittest.main()
