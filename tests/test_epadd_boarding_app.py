"""The Boarding Party tile: the whole chain, with the REAL route condition.

THE GAP THIS FILLS. `test_epadd_registry` drives the app list with a `_FakeTask` whose
`eval_code_checked` returns a canned answer, so a route's `if` is never actually run.
Every shipped app in LM's `consoles/epadd.mast` carries one, and the Boarding Party tile
is gated on `boarding_relevant()` - so the suite could be entirely green while the tile
was missing from a real bridge. Reported exactly that way: "landing party doesn't present
the boarding app".

So this test runs the REAL expression, through the REAL MAST globals table, against the
REAL invitation the mission opens, and asks the question the player asks: is the tile
there? It fails if

* `boarding_relevant` stops being reachable from MAST (a NameError in a route condition
  is EVAL_ERROR, which hides the tile AND ends the GUI task - see
  `GuiAppDecoratorLabel.test` and `MastAsyncTask.eval_code_checked`);
* it raises for any of the three states a console can be in;
* it answers False while a party is open, or while this console is already down;
* the registration stops reaching the boarding (crew) console, which is where the crew
  read it from once they are on the surface.

It is deliberately written as the MISSION writes it - `gui_app_register(...)` with the
same arguments LM uses, and `//gui/app/boarding_party if boarding_relevant()` - so it
tracks the shipped contract rather than a paraphrase of it.
"""
import sys
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401 - registers the node kinds
from cosmos_dev.mock import sbs

# mast_sbs_procedural does `import sbs` at module scope - the engine module, which does
# not exist off-engine. The mock stands in, exactly as the mission runner arranges. It is
# what BUILDS the MAST globals table, and that table is half of what this file tests.
sys.modules.setdefault("sbs", sbs)
import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401,E402 - publishes the globals
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.mast_node import EVAL_ERROR
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.procedural.boarding import (BOARDING_CONSOLE, boarding_assign,
                                           boarding_clear, boarding_invite,
                                           boarding_invite_close)
from sbs_utils.procedural.gui.boarding_gui import boarding_go_down
from sbs_utils.procedural.gui.epadd import (gui_app_list, gui_app_register,
                                            gui_app_why)
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.spaceobject import SpaceObject

SERVER = 0
HELM = 0x8000000000000031
ENGI = 0x8000000000000032

#: Exactly the registration LM's `consoles/epadd.mast` ships.
APP = dict(tab="boarding_party", title="Boarding Party", icon="epadd.boarding",
           group="Ship", sort=1, description="Join the boarding party, or come back",
           boarding=True)

#: And exactly the route that gates it.
CONDITION = "boarding_relevant()"


class _MastTask:
    """A task that evaluates a route condition the way a real one does.

    `MastAsyncTask.eval_code_checked` is `eval(code, self.eval_globals(), symbols)` with
    EVAL_ERROR on a raise, and `eval_globals()` is the MAST globals table. That table is
    the thing under test: a library function that is not in it is a NameError in every
    route condition that names it, and the tile silently disappears.
    """

    def __init__(self):
        self.errors = []

    def eval_code_checked(self, code, end_on_exception=True):
        try:
            return eval(code, MastGlobals.globals, {})
        except Exception as e:              # noqa: BLE001 - recorded, then asserted on
            self.errors.append(e)
            return EVAL_ERROR


class _Page:
    """Only what the registry and the condition read off a page."""

    def __init__(self, client_id=None):
        self.client_id = client_id
        self.console = None
        self.gui_task = None


class BoardingAppBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        boarding_clear()
        self.addCleanup(boarding_clear)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(SERVER, "test"))
        FrameContext.page = None
        self.task = _MastTask()
        FrameContext.task = self.task
        GuiAppDecoratorLabel.clear()
        self.addCleanup(GuiAppDecoratorLabel.clear)
        for cid in (SERVER, HELM, ENGI):
            GuiClient(cid)
        GuiAppDecoratorLabel("boarding_party", CONDITION)
        gui_app_register(**APP)

    def tearDown(self):
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.context = None

    def titles(self, console="helm", client_id=None):
        # THE CONDITION TAKES NO ARGUMENTS. `//gui/app/boarding_party if
        # boarding_relevant()` is compiled MAST, so the console it answers for is
        # whatever `FrameContext.page` is - not the `client_id` the list is scoped by.
        # The page is therefore part of the shape under test, not harness decoration.
        FrameContext.page = _Page(client_id)
        out = [a["title"] for a in gui_app_list(console, client_id)]
        # A condition that RAISED is not an absent tile, it is a broken one - and it also
        # ends the GUI task on a real bridge. Say which, rather than letting it read as
        # "the app was not offered".
        self.assertEqual([], self.task.errors,
                         f"{CONDITION} raised: {self.task.errors}")
        return out

    def open_a_party(self, *members):
        """What `//shared/signal/lp_beam_down` does: offer places, nobody moved yet."""
        ship = SpaceObject()
        ship.id = 9001
        return boarding_invite(ship.id, list(members), title="The Outpost", site=None)

    def somebody(self, name="Ensign Ro"):
        return lifeform_spawn(name, "terran_female", "boarding,security")


class TheNameMustBeReachableFromMast(BoardingAppBase):
    """The cheapest half, and the one that fails the loudest when it goes.

    A route condition is compiled MAST and evaluated against `MastGlobals.globals`. A
    library function that is not published there is a bare NameError at the moment the
    PADD builds its list - the tile vanishes and the console's GUI task ends with it.
    """

    def test_boarding_relevant_is_a_mast_global(self):
        self.assertIn("boarding_relevant", MastGlobals.globals)

    def test_and_so_is_everything_it_leans_on(self):
        """Named individually so a failure says WHICH one went."""
        for name in ("boarding_invitation", "boarding_held", "eva_relevant",
                     "gui_boarding_screen", "boarding_invite", "boarding_invite_crew"):
            with self.subTest(name=name):
                self.assertIn(name, MastGlobals.globals)


class TheTileAppearsWhenAPartyIsOffered(BoardingAppBase):
    """The reported failure, from the player's seat: the hail was answered, the party
    was offered, and the PADD had no Boarding Party tile on it."""

    def test_it_is_NOT_there_before_a_party_exists(self):
        """By design, and it is why the condition is there at all: a mission with no
        landing parties in it used to put "No landing party" on all six consoles."""
        self.assertNotIn("Boarding Party", self.titles())

    def test_IT_IS_THERE_ONCE_ONE_IS_OFFERED(self):
        self.open_a_party(self.somebody())
        self.assertIn("Boarding Party", self.titles())

    def test_on_EVERY_bridge_console(self):
        """`consoles="*"`. The person who answers a landing party call is whoever is
        sitting there, not a particular post."""
        self.open_a_party(self.somebody())
        for console in ("helm", "engineering", "science", "weapons", "comms"):
            with self.subTest(console=console):
                self.assertIn("Boarding Party", self.titles(console))

    def test_and_on_the_crew_console_they_carry_down(self):
        """`boarding=True`. `"*"` does NOT include the crew console - a landing party
        has no use for the cargo hold - so this tile has to opt in, and if it ever stops
        opting in the way BACK up disappears with it."""
        self.open_a_party(self.somebody())
        self.assertIn("Boarding Party", self.titles(BOARDING_CONSOLE))

    def test_a_party_with_an_empty_roster_still_offers_the_tile(self):
        """An invitation whose places are all taken is still a party this console may
        need to read - "who is down there" and the way back are on the same screen."""
        self.open_a_party()
        self.assertIn("Boarding Party", self.titles())


class TheTileStaysWhileYouAreDownThere(BoardingAppBase):
    """The second half of the condition, and the one that strands a crew if it breaks:
    the invitation closes once everybody has gone, and a console still on the surface
    reaches Beam Up through this tile."""

    def setUp(self):
        super().setUp()
        who = self.somebody()
        self.open_a_party(who)
        boarding_assign(HELM, who)
        self.assertTrue(boarding_go_down(HELM), "the console did not take a character")

    def test_it_is_still_offered_after_the_invitation_closes(self):
        boarding_invite_close()
        self.assertIn("Boarding Party", self.titles("helm", HELM))

    def test_on_the_crew_console_it_wears_while_down_there(self):
        boarding_invite_close()
        self.assertIn("Boarding Party", self.titles(BOARDING_CONSOLE, HELM))

    def test_but_NOT_on_a_console_that_stayed_behind(self):
        """The gate is per console, not global - a bridge that sent nobody down has
        nothing to show once the party is closed."""
        boarding_invite_close()
        self.assertNotIn("Boarding Party", self.titles("helm", ENGI))


class TheConditionNeverRaises(BoardingAppBase):
    """Whatever state it is asked in. An app condition that raises does not merely hide
    its tile: `GuiAppDecoratorLabel.test` goes through `eval_code_checked`, whose default
    is `end_on_exception=True` - so it takes the console's GUI task down with it."""

    def test_with_no_party_no_suit_and_no_console(self):
        self.titles("helm", None)

    def test_with_a_party_open(self):
        self.open_a_party(self.somebody())
        self.titles("helm", HELM)

    def test_from_the_SERVER(self):
        """The server has no character and no suit, and asks anyway."""
        self.open_a_party(self.somebody())
        self.titles("helm", SERVER)

    def test_with_a_suit_but_no_boarding_party(self):
        """The EVA half of the condition. A console flying a suit is 'relevant' too."""
        from sbs_utils.procedural.eva import KEY_SUIT
        from sbs_utils.procedural.inventory import set_inventory_value
        suit = SpaceObject()
        suit.id = 4242
        set_inventory_value(HELM, KEY_SUIT, suit.id)
        self.assertIn("Boarding Party", self.titles("helm", HELM))


class TheRouteMustExist(BoardingAppBase):
    """The other way a tile goes missing, and it is INVISIBLE on a bridge: an app whose
    `//gui/app/<tab>` route is not registered is dropped from the list with a warning
    logged under a named category, which goes nowhere unless somebody attached a logger.
    """

    def test_no_route_means_no_tile(self):
        GuiAppDecoratorLabel.clear()
        self.open_a_party(self.somebody())
        self.assertNotIn("Boarding Party", self.titles())

    def test_the_route_is_registered_under_the_tab_name(self):
        """A typo either side of this is the whole failure mode."""
        self.assertIn(APP["tab"], GuiAppDecoratorLabel.all)


class WhyIsMyTileNotThere(BoardingAppBase):
    """`gui_app_why` - because three of the four causes are SILENT by design.

    A route condition hides a tile without a word, which is exactly what it is for; a
    scoping miss is silent too; and the missing-route warning went to a named log
    category with no handler on it, so it reached nobody. "The app is just not there"
    has therefore cost a full archaeology session every time it has been reported. This
    turns it into one line.
    """

    def why(self, tab="boarding_party", console="helm", client_id=None):
        FrameContext.page = _Page(client_id)
        return gui_app_why(tab, console, client_id)

    def test_it_names_the_condition_that_is_withholding_it(self):
        answer = self.why()
        self.assertIn(CONDITION, answer)
        self.assertIn("withheld", answer)

    def test_and_says_it_is_offered_once_a_party_opens(self):
        self.open_a_party(self.somebody())
        self.assertIn("offered", self.why())

    def test_it_names_a_missing_route(self):
        GuiAppDecoratorLabel.clear()
        answer = self.why()
        self.assertIn("//gui/app/boarding_party", answer)
        self.assertIn("mastlib", answer)

    def test_it_names_a_registration_that_was_never_made(self):
        answer = self.why("fabricate")
        self.assertIn("not registered", answer)

    def test_it_explains_the_crew_console_opt_in(self):
        """`"*"` does not include the crew console, and that has bitten twice."""
        from sbs_utils.procedural.gui.epadd import gui_app_register as reg
        GuiAppDecoratorLabel("cargo")
        reg("cargo", title="Cargo", consoles="*")
        answer = self.why("cargo", BOARDING_CONSOLE)
        self.assertIn("boarding=True", answer)

    def test_it_names_the_consoles_an_app_is_scoped_to(self):
        from sbs_utils.procedural.gui.epadd import gui_app_register as reg
        GuiAppDecoratorLabel("cargo")
        reg("cargo", title="Cargo", consoles="engineering")
        answer = self.why("cargo", "helm")
        self.assertIn("engineering", answer)
        self.assertIn("helm", answer)


if __name__ == "__main__":
    unittest.main()
