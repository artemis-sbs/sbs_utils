"""A console on the surface has no Back to the bridge.

CONSOLE_SELECT names the bridge post a client picked at console select, and it goes on
naming it after they beam down. So the PADD's Away Team screen declared a back tab to it,
and pressing Back walked a crew member to Helm while their character was standing on a
planet.

It did that by jumping the tab route, which is not the way up. `away_go_up` releases the
character and restores CONSOLE_TYPE; jumping to a console does neither, so the party went
on believing that person was still down there - held by a console that had left.

The way back is BEAM UP, on that same screen. This pins the two halves: the console
really is left holding its character when it is walked off by a console jump (which is
why the back tab must not be offered), and `away_go_up` really does clean up (which is
why the button is enough).
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.gui.away_gui import (away_go_down, away_go_up, away_who,
                                               RETURN_KEY)
from sbs_utils.procedural.gui.console import gui_console_enter
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.spaceobject import SpaceObject

CID = 0x8000000000000029


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


class AwayBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        # The away roster is a module-level table and outlives a sim swap, so a console
        # that never went down still reads as holding somebody from an earlier test.
        from sbs_utils.procedural.away import away_clear
        away_clear()
        self.addCleanup(away_clear)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        # A REAL page: `gui_console_enter` is the door, and it writes a widget list
        # through the page. A stub that only carries a client_id does not reach the
        # thing under test.
        Agent.SHARED.set_inventory_value(
            "__CONSOLE_TYPES__", {"helm": {"display_name": "Helm"},
                                  "away": {"display_name": "Away"}})
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(CID)
        client.page_stack.append(self.page)
        FrameContext.page = self.page
        gui_console_enter(CID, "helm")

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def send_down(self):
        """Put a real character on this console and morph it, the way joining does."""
        from sbs_utils.procedural.away import away_assign
        from sbs_utils.procedural.lifeform import lifeform_spawn
        who = lifeform_spawn("Ensign Ro", "terran_female", "away,security")
        away_assign(CID, who)
        self.assertTrue(away_go_down(CID), "the console did not take a character")
        return who


class TestWhileOnTheSurface(AwayBase):
    def test_the_console_is_playing_somebody(self):
        self.send_down()
        self.assertIsNotNone(away_who(CID))

    def test_AND_THE_SCREEN_DECLARES_NO_BACK_TAB(self):
        """The expression the PADD screen evaluates: `if not away_who(client_id)`."""
        self.send_down()
        self.assertFalse(not away_who(CID), "a back tab would be offered")

    def test_a_console_that_is_NOT_away_still_gets_one(self):
        """The common case - somebody reading the roster from the bridge."""
        self.assertTrue(not away_who(CID), "no back tab for a bridge console")


class TestWhyTheTabWasWrong(AwayBase):
    def test_A_CONSOLE_JUMP_LEAVES_THE_CHARACTER_HELD(self):
        """What Back actually did. The console arrives at Helm still playing somebody."""
        self.send_down()
        gui_console_enter(CID, "helm")                # what the tab route does
        self.assertEqual(get_inventory_value(CID, "CONSOLE_TYPE", None), "helm")
        self.assertIsNotNone(away_who(CID),
                             "the character was released, so this test is stale")

    def test_BEAM_UP_RELEASES_IT(self):
        """And why the button is the whole answer."""
        self.send_down()
        away_go_up(CID)
        self.assertIsNone(away_who(CID))

    def test_beam_up_puts_the_console_back_where_it_came_from(self):
        self.send_down()
        self.assertEqual(get_inventory_value(CID, RETURN_KEY, None), "helm")
        away_go_up(CID)
        self.assertEqual(get_inventory_value(CID, "CONSOLE_TYPE", None), "helm")


if __name__ == "__main__":
    unittest.main()
