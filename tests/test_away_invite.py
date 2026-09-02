"""Joining a landing party, rather than being dealt one.

The original flow dealt characters round-robin across every console and rerouted all of
them at once. That works and it takes the choice away: a console was on the surface
before anybody at it had agreed to go, playing whoever the loop reached.

An invitation is the same information OFFERED instead of applied. It also makes the
surplus honest - dealing had to double consoles up or strand characters, whereas here
whoever wants to go takes somebody and anyone left at their post stays there.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import away as A

HELM, WEAP, SCI = 7, 8, 9


class _Sim:
    time_tick_counter = 0


class InviteBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        A.away_clear()
        A._TEAM.clear()
        self.addCleanup(A.away_clear)
        self.addCleanup(A._TEAM.clear)
        # Three characters to offer. Plain ids: the invitation stores ids and the team
        # map is keyed by client, so nothing here needs a real lifeform.
        self.roster = [101, 102, 103]

    def tearDown(self):
        FrameContext.context = None

    def invite(self, roster=None):
        return A.away_invite(1, roster if roster is not None else self.roster,
                             title="The Shed")


class TestOffering(InviteBase):
    def test_nobody_moves_until_somebody_volunteers(self):
        """The whole point of the change."""
        self.invite()
        self.assertEqual(A.away_team(), set())
        self.assertEqual(A.away_clients(), set())

    def test_the_open_roster_is_everyone_at_first(self):
        self.invite()
        self.assertEqual(A.away_open_roster(), self.roster)

    def test_the_title_travels_with_it(self):
        self.invite()
        self.assertEqual(A.away_invite_title(), "The Shed")

    def test_there_is_no_invitation_before_one_is_made(self):
        self.assertIsNone(A.away_invitation())
        self.assertEqual(A.away_open_roster(), [])


class TestBeamingDown(InviteBase):
    def setUp(self):
        super().setUp()
        self.invite()

    def test_a_console_can_simply_say_yes(self):
        """Defaulting to the first free character - a crew member who does not care
        who they play should not have to choose."""
        got = A.away_beam_down(HELM)
        self.assertEqual(got, 101)
        self.assertEqual(A.away_me(HELM), 101)

    def test_or_pick_somebody(self):
        self.assertEqual(A.away_beam_down(HELM, 103), 103)
        self.assertEqual(A.away_me(HELM), 103)

    def test_a_character_who_is_taken_is_no_longer_offered(self):
        A.away_beam_down(HELM, 102)
        self.assertEqual(A.away_open_roster(), [101, 103])

    def test_two_consoles_cannot_take_the_same_character(self):
        A.away_beam_down(HELM, 101)
        self.assertIsNone(A.away_beam_down(WEAP, 101))
        self.assertEqual(A.away_me(WEAP), None)

    def test_the_party_can_run_out(self):
        """Answered as 'full', not as an error - a caller shows it, it does not
        raise on the crew."""
        for cid in (HELM, WEAP, SCI):
            self.assertIsNotNone(A.away_beam_down(cid))
        self.assertIsNone(A.away_beam_down(11))
        self.assertEqual(A.away_open_roster(), [])

    def test_nobody_can_join_without_an_invitation(self):
        A.away_invite_clear()
        self.assertIsNone(A.away_beam_down(HELM))

    def test_a_closed_invitation_takes_no_more(self):
        A.away_beam_down(HELM)
        A.away_invite_close()
        self.assertIsNone(A.away_beam_down(WEAP))

    def test_but_whoever_is_down_stays_down(self):
        A.away_beam_down(HELM)
        A.away_invite_close()
        self.assertEqual(A.away_me(HELM), 101)


class TestBeamingUp(InviteBase):
    def setUp(self):
        super().setUp()
        self.invite()
        A.away_beam_down(HELM, 101)

    def test_leaving_releases_the_character(self):
        self.assertTrue(A.away_beam_up(HELM))
        self.assertIsNone(A.away_me(HELM))
        self.assertEqual(A.away_team(), set())

    def test_and_somebody_else_can_take_them(self):
        A.away_beam_up(HELM)
        self.assertIn(101, A.away_open_roster())
        self.assertEqual(A.away_beam_down(WEAP, 101), 101)

    def test_leaving_when_you_are_not_down_is_not_an_error(self):
        self.assertFalse(A.away_beam_up(WEAP))


class TestReset(InviteBase):
    def test_the_invitation_does_not_survive_the_mission(self):
        self.invite()
        A.away_clear()
        self.assertIsNone(A.away_invitation())
        self.assertEqual(A.away_invite_count(), 0)

    def test_it_is_on_the_reset_ledger(self):
        """An unregistered container is invisible to the restart soak."""
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("away invitation", _RESET_PROBES)



class TestTheConsoleHalf(InviteBase):
    """`away_beam_down` takes a character; `away_go_down` turns the console into
    somebody. Separate, because a headless test, a mission script and a soak all want
    to move the team without a console in the way."""

    def setUp(self):
        super().setUp()
        from sbs_utils.gui import GuiClient
        from sbs_utils.procedural.gui import away_gui
        self.gui = away_gui
        GuiClient(HELM)
        self.invite()

    def value(self, key):
        from sbs_utils.procedural.inventory import get_inventory_value
        return get_inventory_value(HELM, key, None)

    def test_going_down_morphs_the_console(self):
        from sbs_utils.procedural.roles import has_role
        self.assertIsNotNone(A.away_beam_down(HELM))
        self.assertTrue(self.gui.away_go_down(HELM))
        self.assertEqual(self.value("CONSOLE_TYPE"), "away")
        self.assertTrue(has_role(HELM, "away"))

    def test_it_remembers_the_post_to_come_back_to(self):
        from sbs_utils.procedural.gui.console import gui_console_enter
        gui_console_enter(HELM, "science")
        A.away_beam_down(HELM)
        self.gui.away_go_down(HELM)
        self.assertEqual(self.value("AWAY_RETURN"), "science")

    def test_coming_back_restores_that_post(self):
        from sbs_utils.procedural.gui.console import gui_console_enter
        from sbs_utils.procedural.roles import has_role
        gui_console_enter(HELM, "science")
        A.away_beam_down(HELM)
        self.gui.away_go_down(HELM)
        self.assertTrue(self.gui.away_go_up(HELM))
        self.assertEqual(self.value("CONSOLE_TYPE"), "science")
        self.assertFalse(has_role(HELM, "away"),
                         "the away role outlived the away console")

    def test_coming_back_frees_the_character(self):
        A.away_beam_down(HELM, 102)
        self.gui.away_go_down(HELM)
        self.gui.away_go_up(HELM)
        self.assertIn(102, A.away_open_roster())

    def test_going_down_without_a_character_does_nothing(self):
        self.assertFalse(self.gui.away_go_down(HELM))

    def test_who_this_console_is(self):
        A.away_beam_down(HELM, 103)
        self.assertEqual(self.gui.away_who(HELM), 103)

    def test_a_console_speaking_for_two_can_choose_which(self):
        """The gap that stopped the PADD replacing the away screen: the deduped
        choice list collapses shared options onto the primary."""
        A.away_beam_down(HELM, 101)
        A.away_assign_also(HELM, 102)
        self.assertEqual(self.gui.away_who(HELM), 101)
        self.gui.away_set_who(HELM, 102)
        self.assertEqual(self.gui.away_who(HELM), 102)

    def test_it_cannot_be_set_to_somebody_this_console_does_not_hold(self):
        A.away_beam_down(HELM, 101)
        self.gui.away_set_who(HELM, 103)
        self.assertEqual(self.gui.away_who(HELM), 101)

if __name__ == "__main__":
    unittest.main()


class TestTheAppOnlyExistsWhenItIsUseful(InviteBase):
    """A playtest reported six consoles each carrying a button that read "No landing
    party". A mission with no away content in it should not show the app at all."""

    def setUp(self):
        super().setUp()
        from sbs_utils.gui import GuiClient
        from sbs_utils.procedural.gui.away_gui import away_relevant
        from sbs_utils.procedural.gui import away_gui
        self.gui = away_gui
        self.relevant = away_relevant
        GuiClient(HELM)

    def test_no_party_and_nobody_down_means_no_app(self):
        self.assertFalse(self.relevant(HELM))

    def test_an_open_invitation_makes_it_relevant_to_everybody(self):
        self.invite()
        self.assertTrue(self.relevant(HELM))
        self.assertTrue(self.relevant(WEAP))

    def test_a_console_that_is_down_keeps_it(self):
        """Even once the invitation closes - it is how they get back."""
        self.invite()
        A.away_beam_down(HELM)
        A.away_invite_close()
        self.assertTrue(self.relevant(HELM))

    def test_and_a_console_that_is_not_down_loses_it(self):
        self.invite()
        A.away_beam_down(HELM)
        A.away_invite_close()
        self.assertFalse(self.relevant(WEAP))

    def test_coming_back_gives_it_up(self):
        self.invite()
        A.away_beam_down(HELM)
        self.gui.away_go_down(HELM)
        A.away_invite_close()
        self.gui.away_go_up(HELM)
        self.assertFalse(self.relevant(HELM))
