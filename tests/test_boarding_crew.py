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
from sbs_utils.procedural import boarding as A
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
        A.boarding_clear()
        A._TEAM.clear()
        A.boarding_forwarding(False)
        self.addCleanup(A.boarding_clear)
        self.addCleanup(A._TEAM.clear)
        self.addCleanup(A.boarding_forwarding, False)
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
        return A.boarding_crew_roster(self.ship, consoles=consoles, assign_missing=False)


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

    def test_every_body_is_on_the_boarding_party(self):
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
        A.boarding_invite_crew(self.ship, title="The Outpost", consoles=[HELM, SCI])

    def test_each_console_has_its_own_character(self):
        self.assertIsNotNone(A.boarding_reserved(HELM))
        self.assertNotEqual(A.boarding_reserved(HELM), A.boarding_reserved(SCI))

    def test_saying_yes_takes_your_own_character_not_the_next_one(self):
        """Without this a console beams down as whoever happens to be first in the
        roster - which is exactly the stranger problem, reintroduced."""
        mine = A.boarding_reserved(SCI)
        self.assertEqual(A.boarding_beam_down(SCI), mine)

    def test_a_reserved_body_is_not_offered_to_anybody_else(self):
        self.assertNotIn(A.boarding_reserved(SCI), A.boarding_open_roster(HELM))

    def test_but_it_is_offered_to_its_own_console(self):
        self.assertIn(A.boarding_reserved(SCI), A.boarding_open_roster(SCI))

    def test_EVEN_WHEN_SOMEBODY_ELSE_IS_FIRST_ON_THE_LIST(self):
        """A mission may add an unreserved specialist to a crew party. Excluding
        other consoles' reservations is then not enough on its own: the free list
        still starts with somebody who is not you, and saying yes would take them.
        """
        from sbs_utils.procedural.lifeform import lifeform_spawn
        invite = A.boarding_invitation()
        extra = lifeform_spawn("Specialist Ito", "", "away, geology")
        invite["roster"] = [extra.id] + list(invite["roster"])
        mine = A.boarding_reserved(SCI)
        self.assertEqual(A.boarding_open_roster(SCI)[0], extra.id)
        self.assertEqual(A.boarding_beam_down(SCI), mine)

    def test_the_reservation_is_the_crew_member(self):
        self.assertEqual(to_object(A.boarding_reserved(SCI)).name, "Sorel")

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
        A.boarding_metric_install()
        self.addCleanup(A.boarding_metric_uninstall)
        self.crew(HELM, "helm", "Marek")
        self.crew(ENG, "engineering", "Kade")
        A.boarding_invite_crew(self.ship, title="The Outpost", consoles=[HELM, ENG])
        for cid in (HELM, ENG):
            A.boarding_beam_down(cid)
        A.boarding_scene_begin(SCENE, "outpost", speaker="outpost")

    def labels(self, client_id):
        return [c.label for c in A.boarding_choices(client_id)]

    def test_nobody_is_qualified_in_the_first_place(self):
        """The fixture has to be short-handed or nothing below is testing anything."""
        self.assertTrue(A.boarding_orphan_choices())

    def test_the_orphaned_job_is_offered_to_the_duty_console(self):
        self.assertIn("Treat her", self.labels(A.boarding_duty_client()))

    def test_AND_TO_NOBODY_ELSE(self):
        """Two consoles offered the same orphaned job is a race nobody knew about."""
        other = ENG if A.boarding_duty_client() == HELM else HELM
        self.assertNotIn("Treat her", self.labels(other))

    def test_the_duty_console_is_stable_across_repaints(self):
        self.assertEqual(A.boarding_duty_client(), A.boarding_duty_client())

    def test_A_STORY_LOCK_IS_NEVER_FORWARDED(self):
        """`learned >= 3` is not "we are short a medic", it is "you have not worked
        it out yet" - forwarding it would hand over the answer."""
        self.assertNotIn("Open the shed", self.labels(A.boarding_duty_client()))

    def test_an_open_choice_is_not_duplicated(self):
        self.assertEqual(self.labels(A.boarding_duty_client()).count("Force it"), 1)

    def test_a_forwarded_choice_says_what_it_was_for(self):
        """So the screen can say who is being covered for rather than silently
        handing somebody a job."""
        ch = next(c for c in A.boarding_orphan_choices() if c.label == "Treat her")
        self.assertIn("medical", ch.get("forwarded"))

    def test_it_can_actually_be_taken(self):
        cid = A.boarding_duty_client()
        index = self.labels(cid).index("Treat her")
        self.assertTrue(A.boarding_answer(cid, index, seq=A.boarding_seq()))

    def test_forwarding_off_hides_it_again(self):
        A.boarding_forwarding(False)
        self.assertNotIn("Treat her", self.labels(A.boarding_duty_client()))

    def test_a_qualified_party_forwards_nothing(self):
        self.crew(SCI, "science", "Sorel", roles="medical")
        body = A.boarding_crew_roster(self.ship, consoles=[SCI], assign_missing=False)[0]
        A.boarding_assign(SCI, body)
        self.assertEqual(A.boarding_orphan_choices(), [])


if __name__ == "__main__":
    unittest.main()


class TestAConsoleThatArrivesLate(CrewPartyBase):
    """The window used to be a moment wide.

    `boarding_invite_crew` casts from the consoles linked to the ship AT THE INSTANT IT
    RUNS, and a mission opens its party when the WORLD says so - Storm's Beacon opens one
    the moment a relic finishes building, which is before anybody has picked a station. So
    the party was cast from an almost empty bridge and everyone who connected afterwards
    was told "The party is full". Owner-reported from a bridge: "consoles that connect
    late need to be able to. The window is way too tight for clients connecting."
    """

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural.links import link
        from sbs_utils.procedural.spawn import player_spawn
        # A REAL SHIP, because this is the one crew-party test that does not hand the
        # console list in: latecomers are found through `linked_to(ship, "consoles")`,
        # and a link to a bare integer that is nobody is silently dropped.
        self.link = link
        self.ship = player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser")
        self.crew(HELM, "helm", "Marek")
        link(self.ship, "consoles", HELM)
        A.boarding_invite_crew(self.ship, title="The Outpost")

    def test_the_party_opened_with_only_the_one_console(self):
        self.assertIsNotNone(A.boarding_reserved(HELM))
        self.assertIsNone(A.boarding_reserved(SCI))

    def test_a_console_that_connects_later_gets_a_place(self):
        self.crew(SCI, "science", "Sorel", roles="medical")
        self.link(self.ship, "consoles", SCI)
        A.boarding_latecomers()
        mine = A.boarding_reserved(SCI)
        self.assertIsNotNone(mine, "a console that arrived late must still be able to go")
        self.assertEqual(to_object(mine).name, "Sorel")

    def test_they_are_on_the_roster_too(self):
        """Reserved but off the roster is the same dead end wearing a different hat:
        `boarding_reserved` only answers for a body the roster still carries."""
        self.crew(SCI, "science", "Sorel")
        self.link(self.ship, "consoles", SCI)
        A.boarding_latecomers()
        self.assertIn(A.boarding_reserved(SCI), A.boarding_invitation()["roster"])

    def test_it_still_works_after_somebody_has_ALREADY_gone(self):
        """The mission-side workaround stopped the moment the first person went out,
        which left the genuinely late console - the one this is all for - with nothing."""
        A.boarding_beam_down(HELM)
        self.crew(SCI, "science", "Sorel")
        self.link(self.ship, "consoles", SCI)
        A.boarding_latecomers()
        self.assertIsNotNone(A.boarding_reserved(SCI))

    def test_asking_twice_does_not_spawn_a_second_body(self):
        """`_body_for` spawns a lifeform every call, so a reconcile that is not identity
        leaks one crew member per console per pass."""
        self.crew(SCI, "science", "Sorel")
        self.link(self.ship, "consoles", SCI)
        A.boarding_latecomers()
        mine = A.boarding_reserved(SCI)
        self.assertEqual(A.boarding_latecomers(), [])
        self.assertEqual(A.boarding_reserved(SCI), mine)

    def test_re_inviting_keeps_the_people_it_already_had(self):
        """A mission is free to re-derive its party; doing so must not re-cast it."""
        was = A.boarding_reserved(HELM)
        A.boarding_invite_crew(self.ship, title="The Outpost")
        self.assertEqual(A.boarding_reserved(HELM), was)

    def test_the_main_screen_is_still_not_a_person(self):
        GuiClient(SCREEN)
        add_role(SCREEN, "mainscreen")
        self.link(self.ship, "consoles", SCREEN)
        A.boarding_latecomers()
        self.assertIsNone(A.boarding_reserved(SCREEN))

    def test_a_mission_authored_cast_never_grows(self):
        """A party a MISSION wrote is three named people on purpose. Only a crew-derived
        one is "whoever is here"."""
        A.boarding_clear()
        body = A.lifeform_spawn("Ensign Vale", "", "boarding") \
            if hasattr(A, "lifeform_spawn") else None
        from sbs_utils.procedural.lifeform import lifeform_spawn
        body = body or lifeform_spawn("Ensign Vale", "", "boarding")
        A.boarding_invite(self.ship, [body], title="The Outpost")
        self.crew(SCI, "science", "Sorel")
        self.link(self.ship, "consoles", SCI)
        self.assertEqual(A.boarding_latecomers(), [])
        self.assertIsNone(A.boarding_reserved(SCI))
