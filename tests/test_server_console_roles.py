"""The SERVER console is a console: roles and inventory reach client id 0.

THE BUG. `to_object(0)` returns None on purpose - for a space object, 0 means "no
object" - and `add_role` / `set_inventory_value` resolved through it. So every write
aimed at the server console was a silent no-op, while `get_inventory_value` (which has
carried an explicit `Agent.get(0)` branch for years) could still read it.

WHAT IT COST. LegendaryMissions' main screen runs `add_role(client_id, "console,
mainscreen")` on its own console, and its comment says out loud why: "anything that
addresses an audience narrows with any_role(...) -- overlays, announce(), comms
targeting -- so a screen with CONSOLE_TYPE but no role is invisible to all of them and
the message is dropped in silence." On the SERVER window - which is the main screen in
an ordinary setup - the role was never added, so an incoming hail placed on the main
screen, every hero card and every lower third resolved to an empty audience and drew
nothing at all.

    python -m unittest tests.test_server_console_roles
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock
from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.gui.overlay import consoles_of
from sbs_utils.procedural.inventory import (get_inventory_value, set_inventory_value,
                                            remove_inventory_value, has_inventory_value)
from sbs_utils.procedural.links import (link, unlink, linked_to, has_link_to,
                                        set_dedicated_link, get_dedicated_link,
                                        clear_dedicated_link)
from sbs_utils.procedural.query import to_agent_list, to_object_list, to_id
from sbs_utils.procedural.roles import (add_role, remove_role, has_role, has_roles,
                                        has_any_role, get_role_list, get_role_string,
                                        role, any_role)
from sbs_utils.procedural.spawn import player_spawn

SERVER = 0
REMOTE = 0x8000000000000002


class ServerConsoleRolesTests(unittest.TestCase):

    def setUp(self):
        mock.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock.sim, mock, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        for cid in (SERVER, REMOTE):
            agent = Agent()
            agent.id = cid
            agent.add()
            link(self.ship, "consoles", cid)

    # --- roles --------------------------------------------------------------

    def test_the_server_can_be_given_a_role(self):
        add_role(SERVER, "mainscreen")
        self.assertIn(SERVER, role("mainscreen"))

    def test_has_role_answers_for_the_server(self):
        add_role(SERVER, "mainscreen")
        self.assertTrue(has_role(SERVER, "mainscreen"))
        self.assertFalse(has_role(SERVER, "comms"))

    def test_has_roles_and_has_any_role_answer_for_the_server(self):
        add_role(SERVER, "console")
        add_role(SERVER, "mainscreen")
        self.assertTrue(has_roles(SERVER, "console,mainscreen"))
        self.assertTrue(has_any_role(SERVER, "comms,mainscreen"))
        self.assertFalse(has_any_role(SERVER, "comms,science"))

    def test_a_role_the_server_can_gain_it_can_also_lose(self):
        # Asymmetry here would be worse than the original bug: a console that could be
        # given a console role and never stripped of one would keep every console it
        # had ever been.
        add_role(SERVER, "mainscreen")
        remove_role(SERVER, "mainscreen")
        self.assertNotIn(SERVER, role("mainscreen"))
        self.assertFalse(has_role(SERVER, "mainscreen"))

    def test_the_role_list_reads_back_for_the_server(self):
        add_role(SERVER, "console")
        add_role(SERVER, "mainscreen")
        self.assertEqual({"console", "mainscreen"}, set(get_role_list(SERVER)))
        self.assertIn("mainscreen", get_role_string(SERVER))

    def test_a_set_of_consoles_includes_the_server(self):
        add_role({SERVER, REMOTE}, "mainscreen")
        self.assertEqual({SERVER, REMOTE}, role("mainscreen"))

    # --- what it was breaking ----------------------------------------------

    def test_an_overlay_narrowed_to_mainscreen_reaches_the_server(self):
        add_role(SERVER, "console")
        add_role(SERVER, "mainscreen")
        self.assertIn(SERVER, consoles_of(self.ship))
        self.assertEqual({SERVER}, consoles_of(self.ship, "mainscreen"))

    def test_the_server_is_narrowed_out_when_it_is_not_the_main_screen(self):
        add_role(REMOTE, "console")
        add_role(REMOTE, "mainscreen")
        self.assertEqual({REMOTE}, consoles_of(self.ship, "mainscreen"))

    # --- inventory ----------------------------------------------------------

    def test_the_server_can_be_written_to_as_well_as_read(self):
        set_inventory_value(SERVER, "CONSOLE_TYPE", "mainscreen")
        self.assertEqual("mainscreen", get_inventory_value(SERVER, "CONSOLE_TYPE"))

    def test_removing_an_inventory_value_reaches_the_server(self):
        set_inventory_value(SERVER, "CONSOLE_TYPE", "mainscreen")
        remove_inventory_value(SERVER, "CONSOLE_TYPE")
        self.assertIsNone(get_inventory_value(SERVER, "CONSOLE_TYPE"))

    def test_has_inventory_value_finds_the_server(self):
        # Agent.has_inventory_set already returns {0} - it is the resolve of that set
        # that dropped the server, so a value written to the console was invisible to
        # the query that goes looking for it.
        set_inventory_value(SERVER, "CONSOLE_TYPE", "mainscreen")
        self.assertIn(SERVER, has_inventory_value("CONSOLE_TYPE", "mainscreen"))

    # --- links --------------------------------------------------------------

    def test_a_link_from_the_server_can_be_created_and_read(self):
        # `linked_to` and `has_link_to` resolve through Agent.resolve_py_object, so they
        # have always READ id 0. Only the write refused it - a link on the server could
        # be looked for and never made.
        link(SERVER, "watching", self.ship)
        self.assertEqual({self.ship}, linked_to(SERVER, "watching"))
        self.assertTrue(has_link_to(SERVER, "watching", self.ship))

    def test_a_link_the_server_can_gain_it_can_also_lose(self):
        link(SERVER, "watching", self.ship)
        unlink(SERVER, "watching", self.ship)
        self.assertEqual(set(), linked_to(SERVER, "watching"))

    def test_a_dedicated_link_reaches_the_server(self):
        set_dedicated_link(SERVER, "following", self.ship)
        self.assertEqual(self.ship, get_dedicated_link(SERVER, "following"))
        clear_dedicated_link(SERVER, "following")
        self.assertIsNone(get_dedicated_link(SERVER, "following"))

    # --- the line that must NOT move ---------------------------------------

    def test_to_object_list_still_refuses_id_zero(self):
        # Space-object callers keep the old meaning: for them 0 really is "no object",
        # and resurrecting it there is how a query starts returning a console.
        self.assertEqual([], to_object_list([SERVER]))
        self.assertEqual([SERVER], [a.id for a in to_agent_list([SERVER])])

    def test_any_role_is_unchanged_for_ordinary_agents(self):
        add_role(self.ship, "escort")
        self.assertEqual({self.ship}, any_role("escort"))


if __name__ == "__main__":
    unittest.main()
