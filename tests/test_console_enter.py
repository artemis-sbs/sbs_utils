"""gui_console_enter - the one door a console goes through to become something else.

Every transition bug in this area is the same shape: a console arrives somewhere
still carrying what the last screen left on it. The pieces were all known and
written down in half a dozen places; this is the test that they happen together,
in the right order, from one call.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role, has_role
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.gui.console import gui_console_enter
from sbs_utils.procedural.gui.overlay import (overlay_live_clear, overlay_register,
                                              overlay_show)
from sbs_utils.procedural.gui.viewscreen import _VIEWERS, viewscreen_set
from sbs_utils.procedural.gui.viewscreen_claims import (TIER_STORY, viewscreen_claimed,
                                                        viewscreen_owner)


def _card(client_id, content):
    from sbs_utils.procedural.gui.row import gui_row
    from sbs_utils.procedural.gui.text import gui_text
    gui_row("row-height: content;")
    gui_text("$text:x;")


overlay_register("door_test", _card)


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None


class DoorBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _VIEWERS.clear()
        overlay_live_clear()
        self.addCleanup(overlay_live_clear)
        self.addCleanup(TickDispatcher.clear)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

        # Two registered console types, so the role strip has something to strip.
        Agent.SHARED.set_inventory_value(
            "__CONSOLE_TYPES__",
            {"science": {"display_name": "Science"}, "helm": {"display_name": "Helm"}})

        self.cid = 0x8000000000000001
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = self.cid
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(self.cid)
        client.page_stack.append(self.page)

        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.foe = to_id(player_spawn(4000, 0, 0, "Kraken", "raider", "battle"))
        add_role(self.cid, "console")
        add_role(self.cid, "science")
        add_role(self.cid, "mainscreen")
        set_inventory_value(self.cid, "CONSOLE_TYPE", "science")
        link(self.ship, "consoles", self.cid)
        mock_sbs.assign_client_to_ship(self.cid, self.ship)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def slot(self, name="center_hero"):
        r = self.page.overlays.slots.get(name)
        return None if r is None else r.content


class TestTheDoor(DoorBase):

    def test_entering_the_console_it_already_is_changes_nothing(self):
        """A screen is re-entered on EVERY repaint - LM's main screen jumps back to
        itself on the viewscreen signal - so this has to be free, or putting the call
        at the top of a console label would tear down what that label just built."""
        overlay_show("center_hero", "door_test", to=self.cid, title="mine")
        self.assertFalse(gui_console_enter(self.cid, "science"))
        self.assertIsNotNone(self.slot(), "a repaint tore down its own card")

    def test_changing_console_reports_the_change(self):
        self.assertTrue(gui_console_enter(self.cid, "helm"))

    def test_it_clears_what_the_last_screen_left_on_the_console(self):
        overlay_show("center_hero", "door_test", to=self.cid, title="stale")
        overlay_show("top_banner", "door_test", to=self.cid, title="stale")
        gui_console_enter(self.cid, "helm")
        self.assertIsNone(self.slot("center_hero"))
        self.assertIsNone(self.slot("top_banner"))

    def test_it_sets_both_the_role_and_the_console_type(self):
        """Role without CONSOLE_TYPE means main-screen view routes never find it;
        CONSOLE_TYPE without the role means overlays, announce() and comms drop the
        message in silence. Both, always."""
        gui_console_enter(self.cid, "helm")
        self.assertTrue(has_role(self.cid, "helm"))
        self.assertTrue(has_role(self.cid, "console"))
        self.assertEqual(get_inventory_value(self.cid, "CONSOLE_TYPE"), "helm")

    def test_it_strips_the_console_role_it_used_to_have(self):
        """Or a screen that used to be a main screen keeps answering as one."""
        gui_console_enter(self.cid, "helm")
        self.assertFalse(has_role(self.cid, "science"))

    def test_it_gives_the_console_its_own_ship_back(self):
        """A shot ASSIGNS its console to the subject, so a console leaving mid-shot
        is riding an enemy."""
        viewscreen_set(self.ship, "orbit", self.foe)
        self.assertEqual(mock_sbs.get_ship_of_client(self.cid), self.foe)
        gui_console_enter(self.cid, "helm")
        self.assertEqual(mock_sbs.get_ship_of_client(self.cid), self.ship)

    def test_it_releases_a_claim_this_console_was_holding(self):
        viewscreen_set(self.ship, "orbit", self.foe, owner="science:%s" % self.cid)
        self.assertTrue(viewscreen_claimed(self.ship))
        gui_console_enter(self.cid, "helm")
        self.assertFalse(viewscreen_claimed(self.ship),
                         "a console that walked away is still holding the screen")

    def test_it_leaves_somebody_elses_claim_alone(self):
        """A ship-wide claim - a hail, docking - is not this console's to give up,
        and a per-console one belonging to a DIFFERENT console certainly is not."""
        viewscreen_set(self.ship, "orbit", self.foe, owner="hail", tier=TIER_STORY)
        gui_console_enter(self.cid, "helm")
        self.assertTrue(viewscreen_claimed(self.ship))
        self.assertEqual(viewscreen_owner(self.ship), "hail")

    def test_an_unknown_console_is_still_a_transition(self):
        """A mission's own console name is not in the registered types; the door must
        still clear and re-label rather than refusing."""
        overlay_show("center_hero", "door_test", to=self.cid, title="stale")
        self.assertTrue(gui_console_enter(self.cid, "gamemaster_overseer"))
        self.assertIsNone(self.slot())
        self.assertEqual(get_inventory_value(self.cid, "CONSOLE_TYPE"),
                         "gamemaster_overseer")


if __name__ == "__main__":
    unittest.main()
