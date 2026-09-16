"""Going down to somebody else's ship, and coming back as yourself.

Two failures live here, and both are silent - the console keeps working, it is just
wrong about who is sitting at it and where they belong.

THE RENAME. `gui_console_enter` re-asserts the crew seat with
`crew_assign(client_id, home, console_type)`, and `own_pick` is None for anybody who was
auto-named. Hand that call the HOST and `crew_resolve` looks the seat up against the
host's roster and hull, then autonames from `_complement_key(host, slot)` - a different
seat, so a different person. `crew_resolve`'s own docstring says it plainly: moving seats
RENAMES an auto-named player. A party that beamed across to a freighter would arrive as
strangers, and the screen would look entirely normal.

THE WAY HOME. `viewscreen_home_ship` falls back to `sbs.get_ship_of_client`, which
boarding has just pointed at the site. So a return that lets the door resolve `home` for
itself puts the console back onto the ship it was trying to leave.

Both are fixed the same way: capture home BEFORE anything moves, pass it explicitly on
both legs, and make the host assignment its own separate line.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.gui.console import gui_console_enter
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.spawn import npc_spawn, player_spawn

# A REAL client id, with the client bit set. `is_client_id` tests `id & 0x8000...`, and
# `camera_assign` resolves its audience through it - so a small integer like 7 resolves to
# no console at all and the assignment silently does nothing. That looks exactly like "the
# return did not re-assign the console", which is the bug this file is about, so the
# harness has to use an id the library would accept from the engine.
CID = 0x8000000000000001


class ReturnBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        A.boarding_clear()
        B.boarding_site_clear()
        GuiClient(CID)
        self.ship = to_object(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.site = to_object(npc_spawn(3000, 0, 3000, "Kestrel", "tsn",
                                        "starbase_civil", "behav_station"))
        sbs.assign_client_to_ship(CID, self.ship.id)
        # Seat them first. `gui_console_enter` only RE-asserts a post that already exists
        # (`crew_post_of` is None otherwise and the whole step is skipped), so without this
        # there is no CREW_NAME for the rename to damage and the class below would pass
        # while proving nothing. This is what the console picker does on a real bridge.
        from sbs_utils.procedural.crew import crew_assign
        crew_assign(CID, self.ship, "science")
        gui_console_enter(CID, "science", ship=self.ship)
        self.who = lifeform_spawn("Lt Marek", "terran_male", "boarding,science")
        A.boarding_invite(self.ship, [self.who], title="The Kestrel")
        A.boarding_beam_down(CID, self.who)

    def post(self, key):
        return get_inventory_value(CID, key, None)


class TheWayDown(ReturnBase):
    def test_it_morphs_to_the_crew_console(self):
        G.boarding_go_down(CID, self.site)
        self.assertEqual("boarding_crew", self.post("CONSOLE_TYPE"))
        self.assertTrue(has_role(CID, "boarding_crew"))

    def test_the_interior_it_sees_is_the_HOST(self):
        G.boarding_go_down(CID, self.site)
        self.assertEqual(self.site.id, sbs.get_ship_of_client(CID))

    def test_but_the_console_still_BELONGS_to_its_own_ship(self):
        G.boarding_go_down(CID, self.site)
        self.assertEqual(self.ship.id, G.boarding_home_ship(CID))

    def test_the_post_it_left_is_remembered(self):
        G.boarding_go_down(CID, self.site)
        self.assertEqual("science", self.post("BOARDING_RETURN"))

    def test_boarding_with_no_host_is_still_the_old_dialogue_morph(self):
        """A mission that only wants menus should not have to invent a site."""
        G.boarding_go_down(CID)
        self.assertEqual("boarding_crew", self.post("CONSOLE_TYPE"))
        self.assertEqual(self.ship.id, sbs.get_ship_of_client(CID))


class TheCrewKeepTheirNames(ReturnBase):
    """The rename, which is the one that would never have been reported as a bug."""

    def setUp(self):
        super().setUp()
        self.name_before = self.post("CREW_NAME")
        self.face_before = self.post("CREW_FACE")

    def test_there_was_a_name_to_keep(self):
        """If the fixture produced no crew post the rest of this class proves nothing."""
        self.assertTrue(self.name_before, "no CREW_NAME to protect - fixture is wrong")

    def test_going_down_does_not_rename_them(self):
        G.boarding_go_down(CID, self.site)
        self.assertEqual(self.name_before, self.post("CREW_NAME"))

    def test_and_coming_back_does_not_either(self):
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        self.assertEqual(self.name_before, self.post("CREW_NAME"))
        self.assertEqual(self.face_before, self.post("CREW_FACE"))


class TheInvitationKnowsWhereYouAreGoing(ReturnBase):
    """A mission says `site=` once; the SHIPPED beam-down button does the rest.

    The ePADD app calls `boarding_go_down(cid)` with no host and knows nothing about
    interiors. Carrying the site on the invitation is what lets that untouched button put
    a party on a floor - otherwise every spatial mission would have to replace the app.
    """

    def test_without_a_site_it_is_still_the_dialogue_party(self):
        G.boarding_go_down(CID)
        self.assertIsNone(B.boarding_my_host(CID))
        self.assertIsNone(B.boarding_my_figure(CID))

    def test_with_one_the_button_lands_them_on_the_interior(self):
        A.boarding_invite(self.ship, [self.who], title="Kepler", site=self.site)
        A.boarding_beam_down(CID, self.who)
        G.boarding_go_down(CID)                       # no host - as the app calls it
        self.assertEqual(self.site.id, B.boarding_my_host(CID))
        self.assertIsNotNone(B.boarding_my_figure(CID))

    def test_they_arrive_at_the_airlock(self):
        """One place, so the party arrives together rather than scattered."""
        A.boarding_invite(self.ship, [self.who], title="Kepler", site=self.site)
        A.boarding_beam_down(CID, self.who)
        G.boarding_go_down(CID)
        self.assertEqual(B.boarding_entry_cell(self.site), B.boarding_where(CID))

    def test_beaming_down_twice_does_not_leave_a_body_behind(self):
        """A reconnect, or moving between sites. An abandoned figure would stand on the
        floor for the rest of the mission and show up in everybody's map."""
        A.boarding_invite(self.ship, [self.who], title="Kepler", site=self.site)
        A.boarding_beam_down(CID, self.who)
        G.boarding_go_down(CID)
        first = B.boarding_my_figure(CID)
        G.boarding_go_down(CID)
        self.assertEqual(first, B.boarding_my_figure(CID))
        self.assertEqual(1, B.boarding_figure_count())

    def test_an_explicit_host_still_wins(self):
        other = to_object(npc_spawn(-9000, 0, 0, "Other", "tsn", "tsn_destroyer",
                                    "behav_station"))
        B.boarding_site_build(other)
        A.boarding_invite(self.ship, [self.who], title="Kepler", site=self.site)
        A.boarding_beam_down(CID, self.who)
        G.boarding_go_down(CID, other)
        self.assertEqual(other.id, B.boarding_my_host(CID))


class TheWayBack(ReturnBase):
    def test_it_lands_on_the_post_it_left(self):
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        self.assertEqual("science", self.post("CONSOLE_TYPE"))

    def test_and_on_its_OWN_ship_not_the_one_it_boarded(self):
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        self.assertEqual(self.ship.id, sbs.get_ship_of_client(CID))
        self.assertNotEqual(self.site.id, sbs.get_ship_of_client(CID))

    def test_the_crew_console_role_does_not_outlive_the_crew_console(self):
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        self.assertFalse(has_role(CID, "boarding_crew"))

    def test_it_stops_driving_anybody(self):
        fig = B.boarding_figure_spawn(self.site, self.who, 10, 10)
        B.boarding_take(CID, fig, self.site)
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        self.assertIsNone(B.boarding_my_figure(CID))
        self.assertIsNone(B.boarding_my_host(CID))

    def test_the_keys_are_cleared_so_a_second_trip_is_clean(self):
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        self.assertIsNone(self.post("BOARDING_RETURN"))
        self.assertIsNone(self.post("BOARDING_HOME_SHIP"))

    def test_a_second_round_trip_still_lands_at_science(self):
        """The remembered post is written only when empty, so a leaked key from the first
        trip would silently pin every later return to the wrong console."""
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        A.boarding_beam_down(CID, self.who)
        G.boarding_go_down(CID, self.site)
        G.boarding_go_up(CID)
        self.assertEqual("science", self.post("CONSOLE_TYPE"))


class NothingButAConsoleReachesTheEngine(ReturnBase):
    """The engine ASSERTS when handed an id that is not a client id.

    Reported from a live run as "a client ID was sent that was not a client ID" - a hard
    stop on a real bridge, not a logged warning. `boarding_go_down` was the one
    `assign_client_to_ship` in the library that reached the engine unfiltered; the three
    in camera.py all sit inside `consoles_of`, which screens ids for exactly this reason.

    The mistake is easy to make from a mission, which is why the guard lives in the
    library rather than in advice: `role("crew")` ALREADY means damcon grid objects
    (LegendaryMissions spawns them `"crew,damcons,lifeform"`), so a loop over a set that
    merely looks like consoles hands this function grid objects.
    """

    def setUp(self):
        super().setUp()
        self.sent = []
        self._real_assign = sbs.assign_client_to_ship

        def spy(cid, sid):
            self.sent.append(cid)
            return self._real_assign(cid, sid)

        sbs.assign_client_to_ship = spy
        self.addCleanup(setattr, sbs, "assign_client_to_ship", self._real_assign)

    def test_a_grid_object_id_never_reaches_the_engine(self):
        fig = B.boarding_figure_spawn(self.site, self.who, 10, 10)
        A.boarding_assign(to_id(fig), self.who)      # pretend a figure is a console
        G.boarding_go_down(to_id(fig), self.site)
        self.assertEqual([], self.sent, "a grid object id was handed to the engine")

    def test_a_real_console_still_does(self):
        """The guard must not be a blanket refusal - the feature needs this call."""
        G.boarding_go_down(CID, self.site)
        self.assertIn(CID, self.sent)

    def test_the_server_console_counts_as_one(self):
        """Client 0 is the server console and is legitimate; `is_client_id` tests the
        0x8000... bit, which 0 does not have - the same carve-out overlay makes."""
        from sbs_utils.procedural.query import is_client_id
        self.assertFalse(is_client_id(0))


class WhenTheSiteIsGone(ReturnBase):
    def test_a_destroyed_host_still_lets_the_console_home(self):
        """Nothing frees a console from a dead host on its own, and the fallback
        (`sbs.get_ship_of_client`) answers with the dead id - so without the captured home
        ship there is no way back at all."""
        G.boarding_go_down(CID, self.site)
        self.site.delete_object()
        G.boarding_go_up(CID)
        self.assertEqual("science", self.post("CONSOLE_TYPE"))
        self.assertEqual(self.ship.id, sbs.get_ship_of_client(CID))


if __name__ == "__main__":
    unittest.main()
