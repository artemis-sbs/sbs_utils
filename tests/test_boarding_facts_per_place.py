"""What a boarding party learns belongs to the PLACE it learned it in.

`; learn x` added to one set for the whole mission, and `learned` counted all of it. So a
second place started with everything the first had taught: a door gated on
`learned >= 2` stood open on arrival, and a return to the same place could not be told
from a first visit to another. Seen in the engine, 2026-10-03 - the facts were still held
after the visit that taught them had ended.

Decided the same day: each place counts only its own, and keeps them for the mission.

Everything here goes in the front door - `boarding_visit`, then the choices pressed.

    python -m unittest tests.test_boarding_facts_per_place
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
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

ENG = 0x8000000000000002

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

## [Scenes](boarding)

### [The Airlock](airlock)
%{learned < 2} Locked.
%{learned >= 2} Open.

- [Read the panel](airlock) if engineering ; learn panel
- [Read the log](airlock) if engineering ; learn log
- [Open the door](airlock) if learned >= 2
- [Return to the ship]()
"""


class FactsBelongToThePlaceTests(unittest.TestCase):
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
        GuiClient(ENG)
        set_inventory_value(ENG, "CONSOLE_TYPE", "engineering")
        link(self.ship, "consoles", ENG)
        crew.crew_assign(ENG, self.ship, "engineering")

    def visit(self, title, **kw):
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "airlock",
                                              title=title, **kw))
        self.assertIsNotNone(A.boarding_beam_down(ENG))

    def labels(self):
        return [amd_choice_label(c.get("label")) for c in A.boarding_choices(ENG)]

    def press(self, starts):
        for i, label in enumerate(self.labels()):
            if label.startswith(starts):
                return A.boarding_answer(ENG, i, A.boarding_seq())
        self.fail("%r is not offered: %r" % (starts, self.labels()))

    def leave(self):
        self.assertTrue(A.boarding_visit_end())

    def test_a_place_counts_what_was_learned_there(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        self.press("Read the log")
        self.assertEqual(A.boarding_learned(), 2)
        self.assertIn("Open the door", self.labels())

    def test_a_second_place_starts_knowing_nothing(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        self.press("Read the log")
        self.leave()
        self.visit("The Wreck")
        self.assertEqual(A.boarding_learned(), 0)
        self.assertNotIn("Open the door", self.labels())

    def test_the_first_line_of_a_new_place_is_gated_on_that_place(self):
        """The room's line is picked as the visit opens - it must not be asked about the
        place the party has just left."""
        self.visit("The Hulk")
        self.press("Read the panel")
        self.press("Read the log")
        self.leave()
        self.visit("The Wreck")
        self.assertEqual(A.boarding_line(), "Locked.")

    def test_coming_back_remembers(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        self.press("Read the log")
        self.leave()
        self.visit("The Wreck")
        self.leave()
        self.visit("The Hulk")
        self.assertEqual(A.boarding_learned(), 2)
        self.assertEqual(A.boarding_line(), "Open.")
        self.assertIn("Open the door", self.labels())

    def test_a_fact_still_counts_once(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        self.press("Read the panel")
        self.assertEqual(A.boarding_learned(), 1)

    def test_the_place_can_be_named_apart_from_the_title(self):
        """Two sites can share a title; the key is what keeps their facts apart."""
        self.visit("Outpost", place="outpost_north")
        self.press("Read the panel")
        self.leave()
        self.visit("Outpost", place="outpost_south")
        self.assertEqual(A.boarding_learned(), 0)
        self.assertEqual(A.boarding_facts("outpost_north"), ["panel"])

    def test_a_route_can_ask_after_the_visit_has_ended(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        self.leave()
        self.assertEqual(A.boarding_facts(), [])                 # nowhere, now
        self.assertEqual(A.boarding_facts("The Hulk"), ["panel"])
        self.assertEqual(A.boarding_learned("panel", "The Hulk"), 1)

    def test_a_place_can_be_made_to_forget(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        self.leave()
        A.boarding_facts_forget("The Hulk")
        self.visit("The Hulk")
        self.assertEqual(A.boarding_learned(), 0)

    def test_the_mission_reset_forgets_every_place(self):
        self.visit("The Hulk")
        self.press("Read the panel")
        A.boarding_clear()
        self.assertEqual(A.boarding_facts("The Hulk"), [])


class ASceneWithNoPlaceKeepsItsOnePoolTests(unittest.TestCase):
    """A mission that drives scenes by hand and never opens a visit or a titled party
    gets the single pool it always had."""

    def setUp(self):
        reset_mock(sbs)
        A.boarding_clear()
        self.addCleanup(A.boarding_clear)

    def test_learn_and_learned_agree_with_no_place(self):
        A._boarding_learn_outcome(None, None, ("cold",))
        self.assertEqual(A.boarding_place(), "")
        self.assertEqual(A.boarding_learned(), 1)
        self.assertEqual(A.boarding_facts(), ["cold"])


if __name__ == "__main__":
    unittest.main()
