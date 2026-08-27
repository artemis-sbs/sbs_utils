"""A second console may LOOK at a selection surface without touching it.

THE GAP. A console selection lives on the SHIP's blob, not on the console -
``grid_selected_UID`` and friends are one value per ship, written by whichever console
clicked last. The library's only lever for suppressing it, ``inc_disable_selection``,
counts on the ship too, so it cannot say "this ONE console does not select": switch it
on so a display-only view cannot click and the console that is meant to be driving
stops selecting as well. And when it does fire it still WRITES - ``target = 0`` - so it
CLEARS the shared selection rather than leaving it alone.

That makes "show the same interior on the main screen, read-only" unexpressible, which
is exactly what an away-mission board needs: the captain drives the grid, the main
screen shows the room the same picture. It bites stock play too - two engineers on one
ship already fight over the grid selection.

``inc_disable_client_selection(client_id, uid)`` is the per-console form. It refuses the
click outright: no blob write, no ``prev_selection`` stomp, no per-client copy.

    python -m unittest tests.test_display_only_console
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock
from sbs_utils.agent import Agent
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import (
    to_id, get_grid_selection, set_grid_selection, get_science_selection,
    inc_disable_selection, inc_disable_client_selection, dec_disable_client_selection,
    inc_disable_client_grid_selection, dec_disable_client_grid_selection,
)
from sbs_utils.procedural.spawn import player_spawn, npc_spawn

GRID = "grid_selected_UID"
SCIENCE = "science_target_UID"
CAPTAIN = 0x8000000000000001
SCREEN = 0x8000000000000002


class DisplayOnlyConsoleTests(unittest.TestCase):

    def setUp(self):
        mock.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock.sim, mock, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.alice = to_id(npc_spawn(100, 0, 0, "Alice", "tsn", "Shuttle", "behav_npcship"))
        self.bob = to_id(npc_spawn(200, 0, 0, "Bob", "tsn", "Shuttle", "behav_npcship"))
        for cid in (CAPTAIN, SCREEN):
            agent = Agent()
            agent.id = cid
            agent.add()
            link(self.ship, "consoles", cid)

    def _click(self, client_id, selected_id, console=GRID):
        """Drive the dispatcher the way a real console click does."""
        event = FakeEvent()
        event.client_id = client_id
        event.origin_id = self.ship
        event.selected_id = selected_id
        event.parent_id = self.ship
        event.extra_tag = console
        event.value_tag = "grid_object_list"
        ConsoleDispatcher.do_select(event, console)

    # --- the behavior that made this necessary ------------------------------

    def test_any_console_can_change_the_shared_selection(self):
        # Not a bug, just the model: one selection per SHIP.
        self._click(CAPTAIN, self.alice)
        self.assertEqual(get_grid_selection(self.ship), self.alice)
        self._click(SCREEN, self.bob)
        self.assertEqual(get_grid_selection(self.ship), self.bob)

    def test_the_ship_level_disable_silences_every_console(self):
        # THE REASON the per-console form exists. Disabling it so the main screen
        # cannot click takes the captain's console down with it.
        inc_disable_selection(self.ship, GRID)
        self._click(CAPTAIN, self.alice)
        self.assertEqual(get_grid_selection(self.ship), 0,
                         "the ship-level disable is all-or-nothing")

    def test_the_ship_level_disable_clears_rather_than_refuses(self):
        set_grid_selection(self.ship, self.alice)
        inc_disable_selection(self.ship, GRID)
        self._click(SCREEN, self.bob)
        self.assertEqual(get_grid_selection(self.ship), 0,
                         "it writes 0 - a held selection is destroyed, not preserved")

    # --- the per-console form -----------------------------------------------

    def test_a_display_console_cannot_change_the_selection(self):
        set_grid_selection(self.ship, self.alice)
        inc_disable_client_grid_selection(SCREEN)
        self._click(SCREEN, self.bob)
        self.assertEqual(get_grid_selection(self.ship), self.alice,
                         "the display console's click must leave the selection alone")

    def test_the_driving_console_still_selects(self):
        inc_disable_client_grid_selection(SCREEN)
        self._click(CAPTAIN, self.bob)
        self.assertEqual(get_grid_selection(self.ship), self.bob,
                         "disabling one console must not silence the others")

    def test_a_refused_click_does_not_stomp_prev_selection(self):
        self._click(CAPTAIN, self.alice)
        self._click(CAPTAIN, self.bob)     # prev_selection is now alice
        before = get_inventory_value(self.ship, "prev_selection", None)
        self.assertEqual(before, self.alice)
        inc_disable_client_grid_selection(SCREEN)
        self._click(SCREEN, self.alice)
        self.assertEqual(get_inventory_value(self.ship, "prev_selection", None), before,
                         "a refused click must not rewrite the undo value either")

    def test_a_refused_click_does_not_write_the_per_client_copy(self):
        inc_disable_client_grid_selection(SCREEN)
        self._click(SCREEN, self.bob)
        self.assertEqual(get_inventory_value(SCREEN, GRID.upper(), 0), 0)

    def test_the_count_nests(self):
        set_grid_selection(self.ship, self.alice)
        inc_disable_client_grid_selection(SCREEN)
        inc_disable_client_grid_selection(SCREEN)
        dec_disable_client_grid_selection(SCREEN)
        self._click(SCREEN, self.bob)
        self.assertEqual(get_grid_selection(self.ship), self.alice,
                         "still held by the second inc")
        dec_disable_client_grid_selection(SCREEN)
        self._click(SCREEN, self.bob)
        self.assertEqual(get_grid_selection(self.ship), self.bob)

    def test_dec_does_not_go_negative(self):
        # An unbalanced dec must not bank credit that swallows a later inc.
        set_grid_selection(self.ship, self.alice)
        dec_disable_client_grid_selection(SCREEN)
        dec_disable_client_grid_selection(SCREEN)
        inc_disable_client_grid_selection(SCREEN)
        self._click(SCREEN, self.bob)
        self.assertEqual(get_grid_selection(self.ship), self.alice)

    def test_it_is_per_console_not_shared_across_consoles(self):
        inc_disable_client_grid_selection(SCREEN)
        self.assertEqual(get_inventory_value(CAPTAIN, "disable_" + GRID, 0), 0)

    def test_silencing_the_grid_leaves_science_alone(self):
        inc_disable_client_grid_selection(SCREEN)
        self._click(SCREEN, self.bob, console=SCIENCE)
        self.assertEqual(get_science_selection(self.ship), self.bob)

    def test_generic_form_works_for_any_surface(self):
        inc_disable_client_selection(SCREEN, SCIENCE)
        self._click(SCREEN, self.bob, console=SCIENCE)
        self.assertEqual(get_science_selection(self.ship), 0)
        dec_disable_client_selection(SCREEN, SCIENCE)
        self._click(SCREEN, self.bob, console=SCIENCE)
        self.assertEqual(get_science_selection(self.ship), self.bob)


if __name__ == "__main__":
    unittest.main()
