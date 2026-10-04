"""A quest that belongs to one person reaches that person - from `boarding_visit` itself.

Found by the lesson "Personal quests". A section of quests may say who each is for:

    ### [Six Names](six_names)
    ---
    For: medical
    Starts when: at once
    Done when: signal names_read
    ---

  * `boarding_visit` handed out nothing: the mission had to call `boarding_quests_grant`
    itself, in a route of its own, because under `boarding_visit(...)` nobody is aboard
    yet. With no such route: lint clean, an empty log, and no quest.
  * `For: Hale` matched the body's NAME, so a player who had saved a name of their own
    was not Hale, and got nothing.
  * `Reward:` on a personal quest paid nobody: a person aboard has no side.

Everything here goes in the front door: a roster and stories written as AMD, consoles
seated by `crew_assign`, `boarding_visit`, and the visit's own tick.

    python -m unittest tests.test_boarding_personal_quests
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_quests as Q
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.quest import quest_get
from sbs_utils.procedural.quest_driver import quest_payee
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

ENG = 0x8000000000000002
SCI = 0x8000000000000003

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

## [Scenes](boarding)

### [The Airlock](airlock)
% Cold.

- [Return to the ship]()

## [Side Stories](side_stories)

### [Six Names](six_names)
---
For: {who}
Starts when: at once
Done when: signal names_read
---
Read the tags.

### [A Cold Core](cold_core)
---
For: engineering
Starts when: at once
Done when: signal core_read
---
Find out who stopped it.
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        crew.crew_clear()
        A.boarding_clear()
        Q.boarding_quests_clear()
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        self.addCleanup(Q.boarding_quests_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))

    def declare(self, who="medical"):
        text = MISSION.format(who=who)
        crew.crew_declare_amd(amd_document(text, data_parser=amd_crew_data))
        self.scenes = dialogue_scenes(amd_section(amd_document(text), "boarding"))
        self.stories = amd_section(amd_document(text, data_parser=amd_quest_data),
                                   "side_stories")

    def sit(self, client_id, console, **own):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        link(self.ship, "consoles", client_id)
        return crew.crew_assign(client_id, self.ship, console, **own)

    def visit(self, *consoles, stories=True):
        kw = {"stories": self.stories} if stories else {}
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "airlock",
                                              title="The Hulk", **kw))
        for client_id in consoles:
            self.assertIsNotNone(A.boarding_beam_down(client_id))
        A._boarding_visit_tick()


class PersonalQuestTests(_Base):
    def test_the_visit_hands_each_quest_to_its_person(self):
        self.declare()
        self.sit(ENG, "engineering")
        self.sit(SCI, "science")
        self.visit(ENG, SCI)
        self.assertEqual(Q.boarding_quest_owner("six_names"), A.boarding_me(SCI))
        self.assertEqual(Q.boarding_quest_owner("cold_core"), A.boarding_me(ENG))
        self.assertIsNotNone(quest_get(A.boarding_me(SCI), "six_names"))

    def test_without_stories_nothing_is_handed_out(self):
        self.declare()
        self.sit(SCI, "science")
        self.visit(SCI, stories=False)
        self.assertIsNone(Q.boarding_quest_owner("six_names"))

    def test_somebody_who_arrives_later_still_gets_theirs(self):
        self.declare()
        self.sit(ENG, "engineering")
        self.sit(SCI, "science")
        self.visit(ENG)
        self.assertIsNone(Q.boarding_quest_owner("six_names"))
        self.assertIsNotNone(A.boarding_beam_down(SCI))
        A._boarding_visit_tick()
        self.assertEqual(Q.boarding_quest_owner("six_names"), A.boarding_me(SCI))

    def test_nobody_covers_for_a_person(self):
        self.declare()
        self.sit(ENG, "engineering")
        self.visit(ENG)
        self.assertIsNone(Q.boarding_quest_owner("six_names"))

    def test_for_takes_the_roster_key_the_name_or_the_last_name(self):
        for who in ("hale", "Dr Hale", "Hale", "Medical"):
            with self.subTest(who=who):
                self.setUp()
                self.declare(who)
                self.sit(SCI, "science")
                self.visit(SCI)
                self.assertEqual(Q.boarding_quest_owner("six_names"), A.boarding_me(SCI))

    def test_a_player_with_a_name_of_their_own_is_still_the_person(self):
        self.declare("Hale")
        post = self.sit(SCI, "science", own_name="Zed")
        self.assertEqual(post.name, "Zed")
        self.visit(SCI)
        self.assertEqual(Q.boarding_quest_owner("six_names"), A.boarding_me(SCI))

    def test_a_word_nobody_answers_to_goes_to_nobody(self):
        self.declare("medcal")
        self.sit(SCI, "science")
        self.visit(SCI)
        self.assertIsNone(Q.boarding_quest_owner("six_names"))


class RewardTests(_Base):
    def test_a_person_aboard_is_paid_through_their_ship(self):
        self.declare()
        self.sit(SCI, "science")
        self.visit(SCI)
        sbs.assign_client_to_ship(SCI, self.ship)
        self.assertEqual(quest_payee(A.boarding_me(SCI)), self.ship)

    def test_anything_else_is_still_paid_as_itself(self):
        self.declare()
        self.assertEqual(quest_payee(self.ship), self.ship)


if __name__ == "__main__":
    unittest.main()
