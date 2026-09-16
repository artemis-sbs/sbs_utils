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
        self.assertEqual("crew", self.post("CONSOLE_TYPE"))
        self.assertTrue(has_role(CID, "crew"))

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
        self.assertEqual("crew", self.post("CONSOLE_TYPE"))
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
        self.assertFalse(has_role(CID, "crew"))

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
