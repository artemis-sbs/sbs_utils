"""Back, for a console that is not on its ship.

CONSOLE_SELECT names the bridge post a client picked at console select, and it goes on
naming it after they beam down. So the PADD's Boarding Party screen declared a back tab
to it, and pressing Back walked a crew member to Helm while their character was standing
on a planet.

It did that by jumping the tab route, which is not the way up. `boarding_go_up` releases
the character and restores CONSOLE_TYPE; jumping to a console does neither, so the party
went on believing that person was still down there - held by a console that had left.
`TestWhyTheTabWasWrong` still pins both halves of that, and both are still true.

**THE ANSWER CHANGED, and this file changed with it.** The first answer was for the PADD
screen to declare NO back tab while boarded - which fixed the wrong destination by
removing the button, leaving a console with no Back at all. The answer now is a
SUBSTITUTION at `gui_tab_back`, the one choke point that writes `__back_tab__`: a boarded
console goes to the crew console whatever the caller asked for. That is one place rather
than the four call sites in LM's `consoles/epadd.mast` and the ten elsewhere, and "the
guard existed in the page and had been applied in one place only" is a mistake this
codebase has already made and written down.

It is INSTALLED rather than assumed, because the library cannot declare a `//gui/tab` -
sending Back to a tab with no route behind it is no better than sending it to Helm.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.gui.boarding_gui import (boarding_go_down, boarding_go_up, boarding_who,
                                               RETURN_KEY)
from sbs_utils.procedural.gui import console_tab as T
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
        from sbs_utils.procedural.boarding import boarding_clear
        boarding_clear()
        self.addCleanup(boarding_clear)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        # A REAL page: `gui_console_enter` is the door, and it writes a widget list
        # through the page. A stub that only carries a client_id does not reach the
        # thing under test.
        Agent.SHARED.set_inventory_value(
            "__CONSOLE_TYPES__", {"helm": {"display_name": "Helm"},
                                  "boarding": {"display_name": "Away"}})
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
        from sbs_utils.procedural.boarding import boarding_assign
        from sbs_utils.procedural.lifeform import lifeform_spawn
        who = lifeform_spawn("Ensign Ro", "terran_female", "away,security")
        boarding_assign(CID, who)
        self.assertTrue(boarding_go_down(CID), "the console did not take a character")
        return who


CREW_TAB = "boarding_crew"


class TestWhileOnTheSurface(AwayBase):
    """What this class used to assert is now the OPPOSITE of the behaviour: it pinned
    `if not boarding_who(client_id)`, the expression the PADD screen used to skip
    declaring a back tab at all. That expression is gone from the mission, so the tests
    that guarded it are gone too - keeping them would have pinned a screen that no longer
    exists and passed forever without touching the code."""

    def setUp(self):
        super().setUp()
        T.gui_tab_back_while_boarded(CREW_TAB)
        self.addCleanup(T.gui_tab_back_while_boarded, None)

    def back_tab(self, asked="console_select"):
        T.gui_tab_back(asked)
        return get_inventory_value(CID, "__back_tab__", None)

    def test_the_console_is_playing_somebody(self):
        self.send_down()
        self.assertIsNotNone(boarding_who(CID))

    def test_BACK_GOES_TO_THE_CREW_CONSOLE(self):
        self.send_down()
        self.assertEqual(CREW_TAB, self.back_tab())

    def test_whatever_the_caller_asked_for(self):
        """The point of doing it at the choke point: fourteen call sites ask for
        something else and not one of them has to know."""
        self.send_down()
        for asked in ("console_select", "helm", "epadd", "science"):
            self.assertEqual(CREW_TAB, self.back_tab(asked))

    def test_a_console_that_is_NOT_boarded_is_untouched(self):
        """The common case - somebody reading the roster from the bridge."""
        self.assertEqual("helm", self.back_tab("helm"))

    def test_and_neither_is_the_same_console_after_it_beams_up(self):
        self.send_down()
        boarding_go_up(CID)
        self.assertEqual("helm", self.back_tab("helm"))

    def test_the_crew_console_does_not_point_at_ITSELF(self):
        """The crew console declaring its own Back must not be rewritten into a loop
        with nowhere to go."""
        self.send_down()
        self.assertEqual(CREW_TAB, self.back_tab(CREW_TAB))

    def test_the_substituted_tab_is_ENABLED_too(self):
        """A back tab that is not enabled is a button that is not drawn - which is how
        "the Console Back Button is not there sometimes" was reported once already."""
        self.send_down()
        self.back_tab()
        tabs = get_inventory_value(CID, "console_tabs", {})
        self.assertTrue(tabs.get(CREW_TAB))


class TestWhenNothingHasDeclaredATab(AwayBase):
    """Substituting unconditionally would send Back to a tab with no route behind it,
    and a dead Back is no better than one that goes to the wrong place. So a mission that
    has not declared a crew-console tab keeps exactly the old behaviour."""

    def back_tab(self, asked="console_select"):
        T.gui_tab_back(asked)
        return get_inventory_value(CID, "__back_tab__", None)

    def test_a_boarded_console_is_left_alone(self):
        self.assertIsNone(T.gui_tab_boarded_back_tab())
        self.send_down()
        self.assertEqual("console_select", self.back_tab())

    def test_installing_and_clearing_both_take(self):
        self.addCleanup(T.gui_tab_back_while_boarded, None)
        T.gui_tab_back_while_boarded(CREW_TAB)
        self.assertEqual(CREW_TAB, T.gui_tab_boarded_back_tab())
        T.gui_tab_back_while_boarded(None)
        self.assertIsNone(T.gui_tab_boarded_back_tab())
        self.send_down()
        self.assertEqual("console_select", self.back_tab())

    def test_a_blank_name_clears_rather_than_installing_one(self):
        self.addCleanup(T.gui_tab_back_while_boarded, None)
        T.gui_tab_back_while_boarded("   ")
        self.assertIsNone(T.gui_tab_boarded_back_tab())


class TestWhyTheTabWasWrong(AwayBase):
    def test_A_CONSOLE_JUMP_LEAVES_THE_CHARACTER_HELD(self):
        """What Back actually did. The console arrives at Helm still playing somebody."""
        self.send_down()
        gui_console_enter(CID, "helm")                # what the tab route does
        self.assertEqual(get_inventory_value(CID, "CONSOLE_TYPE", None), "helm")
        self.assertIsNotNone(boarding_who(CID),
                             "the character was released, so this test is stale")

    def test_BEAM_UP_RELEASES_IT(self):
        """And why the button is the whole answer."""
        self.send_down()
        boarding_go_up(CID)
        self.assertIsNone(boarding_who(CID))

    def test_beam_up_puts_the_console_back_where_it_came_from(self):
        self.send_down()
        self.assertEqual(get_inventory_value(CID, RETURN_KEY, None), "helm")
        boarding_go_up(CID)
        self.assertEqual(get_inventory_value(CID, "CONSOLE_TYPE", None), "helm")


if __name__ == "__main__":
    unittest.main()
