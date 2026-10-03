"""`boarding_visit`: the party, its scene, and the way home, as one call.

A boarding scene used to have a beginning and no end. A mission opened a party, began a
scene, and when the last room closed nothing happened: the party stayed open, every
console kept the character it was playing, and a console that went down late arrived in a
room with nothing in it. Open Universe's sites had it worse - the scene they began stayed
"open" for the rest of the session, which made every later site arrival end early.

One call owns the whole visit now. It opens the party (the crew as themselves, or a cast
the mission hands it), begins the first room, and when the scene closes it shuts the party,
brings every console home and says so with `boarding_visit_ended`.

    python -m unittest tests.test_boarding_visit
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.amd import amd_choice_label
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

HELM = 0x8000000000000001
SCI = 0x8000000000000002

PLACE = """# [Mission](mission)

## [Scenes](boarding)

### [The Airlock](airlock)
% The outer door was never sealed.

- [Go aft](reactor)
- [Return to the ship]()

### [The Reactor Room](reactor)
% Cold.

- [Go back](airlock)
- [Return to the ship]()
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        TickDispatcher.clear()
        crew.crew_clear()
        A.boarding_clear()
        self.addCleanup(TickDispatcher.clear)
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.scenes = dialogue_scenes(amd_section(
            amd_document(PLACE, data_parser=amd_mission_data), "boarding"))
        self.sit(HELM, "helm")
        self.sit(SCI, "science")
        self.signals = []
        self._emit = A.signal_emit
        A.signal_emit = lambda name, data=None: self.signals.append((name, data))
        self.addCleanup(setattr, A, "signal_emit", self._emit)

    def sit(self, client_id, console):
        """A console on the ship, with whoever the crew system puts at it."""
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        link(self.ship, "consoles", client_id)
        crew.crew_assign(client_id, self.ship, console)

    def advance(self, seconds):
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            TickDispatcher.dispatch_tick()
            sbs.sim._time_tick_counter += 1

    def take(self, client_id, starts_with):
        labels = [amd_choice_label(c.get("label")) for c in A.boarding_choices(client_id)]
        index = next(i for i, text in enumerate(labels) if text.startswith(starts_with))
        A.boarding_answer(client_id, index, A.boarding_seq())

    def ended(self):
        return [d for n, d in self.signals if n == "boarding_visit_ended"]


class TheVisitOpensTests(_Base):
    def test_it_opens_the_party_and_the_first_room(self):
        invite = A.boarding_visit(self.ship, self.scenes, "airlock", title="The Hulk")
        self.assertIsNotNone(invite)
        self.assertIsNotNone(A.boarding_invitation())
        self.assertEqual(A.boarding_invite_title(), "The Hulk")
        self.assertEqual(A.boarding_scene(), "airlock")
        self.assertIsNotNone(A.boarding_visiting())

    def test_with_no_cast_the_party_is_the_crew(self):
        """One identity: who you are on the bridge is who goes aboard."""
        invite = A.boarding_visit(self.ship, self.scenes, "airlock")
        self.assertTrue(invite.get("crew"))
        mine = A.boarding_reserved(HELM)
        self.assertIsNotNone(mine)
        self.assertIn(crew.crew_post_of(HELM).name, to_object(mine).name)

    def test_a_cast_handed_in_is_the_party(self):
        okoro = to_id(lifeform_spawn("Chief Okoro", "", "boarding, engineering"))
        invite = A.boarding_visit(self.ship, self.scenes, "airlock", cast=[okoro])
        self.assertEqual(invite.get("roster"), [okoro])
        self.assertFalse(invite.get("crew", False))

    def test_a_first_room_that_does_not_exist_opens_nothing(self):
        """Checked BEFORE the party opens, or the crew is offered a place with no room."""
        self.assertIsNone(A.boarding_visit(self.ship, self.scenes, "airlok"))
        self.assertIsNone(A.boarding_invitation())
        self.assertIsNone(A.boarding_visiting())

    def test_one_visit_at_a_time(self):
        A.boarding_visit(self.ship, self.scenes, "airlock", title="The Hulk")
        self.assertIsNone(A.boarding_visit(self.ship, self.scenes, "reactor", title="Other"))
        self.assertEqual(A.boarding_invite_title(), "The Hulk")
        self.assertEqual(A.boarding_scene(), "airlock")


class TheVisitEndsTests(_Base):
    def setUp(self):
        super().setUp()
        A.boarding_visit(self.ship, self.scenes, "airlock", title="The Hulk")
        self.assertIsNotNone(A.boarding_beam_down(HELM))

    def test_nothing_ends_while_the_scene_is_open(self):
        self.take(HELM, "Go aft")
        self.advance(3)
        self.assertEqual(A.boarding_scene(), "reactor")
        self.assertIsNotNone(A.boarding_invitation())
        self.assertTrue(A.boarding_held(HELM))
        self.assertEqual(self.ended(), [])

    def test_the_last_choice_closes_the_party_and_brings_the_console_home(self):
        self.take(HELM, "Return to the ship")
        self.assertFalse(A.boarding_is_open())
        self.advance(3)
        self.assertIsNone(A.boarding_invitation())
        self.assertFalse(A.boarding_held(HELM))
        self.assertIsNone(A.boarding_visiting())

    def test_it_says_so_once(self):
        self.take(HELM, "Return to the ship")
        self.advance(6)
        ended = self.ended()
        self.assertEqual(len(ended), 1)
        self.assertEqual(ended[0]["BOARDING_SHIP"], self.ship)
        self.assertEqual(ended[0]["BOARDING_TITLE"], "The Hulk")

    def test_a_second_visit_can_follow_the_first(self):
        """What Open Universe's sites could never do: the scene used to stay open."""
        self.take(HELM, "Return to the ship")
        self.advance(3)
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "reactor", title="Again"))
        self.assertEqual(A.boarding_scene(), "reactor")

    def test_a_mission_can_end_it_early(self):
        self.assertTrue(A.boarding_visit_end())
        self.assertFalse(A.boarding_is_open())
        self.assertIsNone(A.boarding_invitation())
        self.assertFalse(A.boarding_held(HELM))
        self.assertEqual(len(self.ended()), 1)

    def test_ending_twice_is_ending_once(self):
        A.boarding_visit_end()
        self.assertFalse(A.boarding_visit_end())
        self.assertEqual(len(self.ended()), 1)

    def test_the_mission_reset_drops_the_visit(self):
        A.boarding_clear()
        self.assertIsNone(A.boarding_visiting())
        self.advance(3)
        self.assertEqual(self.ended(), [])


class TheTickNeverRaisesTests(_Base):
    """A raising interval callback pauses the sim and cannot be resumed."""

    def test_a_console_that_cannot_be_brought_home_is_still_released(self):
        A.boarding_visit(self.ship, self.scenes, "airlock", title="The Hulk")
        A.boarding_beam_down(HELM)

        def boom(client_id):
            raise RuntimeError("no page for this console")
        real = A._visit_bring_home
        A._visit_bring_home = boom
        self.addCleanup(setattr, A, "_visit_bring_home", real)

        self.take(HELM, "Return to the ship")
        self.advance(3)                      # must not raise
        self.assertFalse(A.boarding_held(HELM))
        self.assertIsNone(A.boarding_invitation())


if __name__ == "__main__":
    unittest.main()
