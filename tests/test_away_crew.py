"""A landing party made of the people already at the consoles.

Two casts was the older shape: a crew post was "a label on a seat occupied by a human"
and an away character "a body in the world", declared in separate files and kept in step
by hand. It works, and it means the person who has been Lt Marek all evening beams down
as a stranger.

The two properties under test are the ones a playtest will notice:

* **You go as yourself.** The body carries the crew member's name, rank and face, and
  the job words a scene guards on. Beaming down is a confirmation, not a casting call.
* **A short party still plays.** A crew party is whoever was on the bridge, so it can
  lack a medic - and the medic's line, and any beat whose only way onward is guarded,
  would simply be lost. It is forwarded instead, to exactly one console.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import away as A
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.roles import add_role, has_role
from sbs_utils.procedural.query import to_object

HELM, SCI, ENG, SCREEN = 7, 8, 9, 10


class _Sim:
    time_tick_counter = 0


class CrewPartyBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        A.away_clear()
        A._TEAM.clear()
        A.away_forwarding(False)
        self.addCleanup(A.away_clear)
        self.addCleanup(A._TEAM.clear)
        self.addCleanup(A.away_forwarding, False)
        self.ship = 1

    def tearDown(self):
        FrameContext.context = None

    def crew(self, client_id, console, name, rank="", roles=None, face=""):
        """Sit somebody at a console, the way `crew_assign` publishes them."""
        GuiClient(client_id)          # inventory lives on the client agent
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        set_inventory_value(client_id, "CREW_NAME", name)
        set_inventory_value(client_id, "CREW_RANK", rank)
        set_inventory_value(client_id, "CREW_FACE", face)
        set_inventory_value(client_id, "CREW_ROLES", roles or "")

    def bodies(self, consoles):
        return A.away_crew_roster(self.ship, consoles=consoles, assign_missing=False)


class TestTheBodyIsTheCrewMember(CrewPartyBase):
    def test_one_body_per_console(self):
        self.crew(HELM, "helm", "Marek")
        self.crew(SCI, "science", "Sorel")
        self.assertEqual(len(self.bodies([HELM, SCI])), 2)

    def test_it_carries_their_name_and_rank(self):
        """You go down as yourself - the whole reason for deriving the party."""
        self.crew(HELM, "helm", "Marek", rank="Lt")
        body = to_object(self.bodies([HELM])[0])
        self.assertEqual(body.name, "Lt Marek")

    def test_a_crew_member_with_no_rank_is_just_their_name(self):
        self.crew(HELM, "helm", "Marek")
        self.assertEqual(to_object(self.bodies([HELM])[0]).name, "Marek")

    def test_authored_roles_become_the_guard_words(self):
        """`Roles:` has always been an accepted crew field and was read no further
        than the roster. This is what makes it mean something."""
        self.crew(SCI, "science", "Sorel", roles="medical, xenobiology")
        body = self.bodies([SCI])[0]
        self.assertTrue(has_role(body, "medical"))
        self.assertTrue(has_role(body, "xenobiology"))

    def test_WITHOUT_ROLES_THE_CONSOLE_IS_THE_GUARD_WORD(self):
        """The fallback the design turns on: a mission that never wrote Roles still
        gates, because the seat they left is who they are."""
        self.crew(SCI, "science", "Sorel")
        self.assertTrue(has_role(self.bodies([SCI])[0], "science"))

    def test_every_body_is_on_the_away_team(self):
        self.crew(HELM, "helm", "Marek")
        self.assertTrue(has_role(self.bodies([HELM])[0], A.CREW_ROLE))

    def test_the_main_screen_takes_no_body(self):
        """It is the whole room's view, not a person."""
        self.crew(HELM, "helm", "Marek")
        self.crew(SCREEN, "mainscreen", "Nobody")
        add_role(SCREEN, "mainscreen")
        self.assertEqual(len(self.bodies([HELM, SCREEN])), 1)

    def test_a_console_with_nobody_at_it_contributes_nobody(self):
        GuiClient(ENG)
        set_inventory_value(ENG, "CONSOLE_TYPE", "engineering")
        self.assertEqual(self.bodies([ENG]), [])


class TestAPlaceHeldForYou(CrewPartyBase):
    def setUp(self):
        super().setUp()
        self.crew(HELM, "helm", "Marek")
        self.crew(SCI, "science", "Sorel", roles="medical")
        A.away_invite_crew(self.ship, title="The Outpost", consoles=[HELM, SCI])

    def test_each_console_has_its_own_character(self):
        self.assertIsNotNone(A.away_reserved(HELM))
        self.assertNotEqual(A.away_reserved(HELM), A.away_reserved(SCI))

    def test_saying_yes_takes_your_own_character_not_the_next_one(self):
        """Without this a console beams down as whoever happens to be first in the
        roster - which is exactly the stranger problem, reintroduced."""
        mine = A.away_reserved(SCI)
        self.assertEqual(A.away_beam_down(SCI), mine)

    def test_a_reserved_body_is_not_offered_to_anybody_else(self):
        self.assertNotIn(A.away_reserved(SCI), A.away_open_roster(HELM))

    def test_but_it_is_offered_to_its_own_console(self):
        self.assertIn(A.away_reserved(SCI), A.away_open_roster(SCI))

    def test_EVEN_WHEN_SOMEBODY_ELSE_IS_FIRST_ON_THE_LIST(self):
        """A mission may add an unreserved specialist to a crew party. Excluding
        other consoles' reservations is then not enough on its own: the free list
        still starts with somebody who is not you, and saying yes would take them.
        """
        from sbs_utils.procedural.lifeform import lifeform_spawn
        invite = A.away_invitation()
        extra = lifeform_spawn("Specialist Ito", "", "away, geology")
        invite["roster"] = [extra.id] + list(invite["roster"])
        mine = A.away_reserved(SCI)
        self.assertEqual(A.away_open_roster(SCI)[0], extra.id)
        self.assertEqual(A.away_beam_down(SCI), mine)

    def test_the_reservation_is_the_crew_member(self):
        self.assertEqual(to_object(A.away_reserved(SCI)).name, "Sorel")

    def test_forwarding_is_turned_on_for_a_crew_party(self):
        """A hand-cast roster missing a medic MEANS something; a crew party missing
        one is an accident of who was on the bridge."""
        self.assertTrue(A.FORWARDING)


#: One beat with three ways on: open to anyone, a JOB nobody present holds, and the
#: story's own lock. Forwarding must reach exactly the middle one.
BODY = """% The door is shut.
- [Force it](inside)
- [Treat her](inside) if medical >= 1
- [Open the shed](inside) if learned >= 3
"""

SCENE = {
    "outpost": {"key": "outpost", "display_text": "outpost", "description": BODY,
                "data": {"speaker": "outpost"}},
    "inside": {"key": "inside", "display_text": "inside",
               "description": "% You are in.\n", "data": {"speaker": "outpost"}},
}


class TestAPartyShortOfPeople(CrewPartyBase):
    """Nobody down there is a medic. The medic's line still has to be playable."""

    def setUp(self):
        super().setUp()
        A.away_metric_install()
        self.addCleanup(A.away_metric_uninstall)
        self.crew(HELM, "helm", "Marek")
        self.crew(ENG, "engineering", "Kade")
        A.away_invite_crew(self.ship, title="The Outpost", consoles=[HELM, ENG])
        for cid in (HELM, ENG):
            A.away_beam_down(cid)
        A.away_scene_begin(SCENE, "outpost", speaker="outpost")

    def labels(self, client_id):
        return [c.label for c in A.away_choices(client_id)]

    def test_nobody_is_qualified_in_the_first_place(self):
        """The fixture has to be short-handed or nothing below is testing anything."""
        self.assertTrue(A.away_orphan_choices())

    def test_the_orphaned_job_is_offered_to_the_duty_console(self):
        self.assertIn("Treat her", self.labels(A.away_duty_client()))

    def test_AND_TO_NOBODY_ELSE(self):
        """Two consoles offered the same orphaned job is a race nobody knew about."""
        other = ENG if A.away_duty_client() == HELM else HELM
        self.assertNotIn("Treat her", self.labels(other))

    def test_the_duty_console_is_stable_across_repaints(self):
        self.assertEqual(A.away_duty_client(), A.away_duty_client())

    def test_A_STORY_LOCK_IS_NEVER_FORWARDED(self):
        """`learned >= 3` is not "we are short a medic", it is "you have not worked
        it out yet" - forwarding it would hand over the answer."""
        self.assertNotIn("Open the shed", self.labels(A.away_duty_client()))

    def test_an_open_choice_is_not_duplicated(self):
        self.assertEqual(self.labels(A.away_duty_client()).count("Force it"), 1)

    def test_a_forwarded_choice_says_what_it_was_for(self):
        """So the screen can say who is being covered for rather than silently
        handing somebody a job."""
        ch = next(c for c in A.away_orphan_choices() if c.label == "Treat her")
        self.assertIn("medical", ch.get("forwarded"))

    def test_it_can_actually_be_taken(self):
        cid = A.away_duty_client()
        index = self.labels(cid).index("Treat her")
        self.assertTrue(A.away_answer(cid, index, seq=A.away_seq()))

    def test_forwarding_off_hides_it_again(self):
        A.away_forwarding(False)
        self.assertNotIn("Treat her", self.labels(A.away_duty_client()))

    def test_a_qualified_party_forwards_nothing(self):
        self.crew(SCI, "science", "Sorel", roles="medical")
        body = A.away_crew_roster(self.ship, consoles=[SCI], assign_missing=False)[0]
        A.away_assign(SCI, body)
        self.assertEqual(A.away_orphan_choices(), [])


if __name__ == "__main__":
    unittest.main()
