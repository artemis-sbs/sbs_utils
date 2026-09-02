"""ePADD belongs on consoles, and nowhere else.

Reported from the Gamma with a Q playtest, 2026-09-01: "The ePADD also shows up on the
top way too much. It should not be at the start screen, console select, main screen,
game results. Only on the consoles."

`gui_app_mode_is_on` is a per-client/mission flag - it says the MISSION wants ePADD, not
that the screen being drawn is a console. Nothing tested the latter, so the button
replaced the strip on every build that queued one.

The discriminator is two per-build facts, and the tests below exist because neither
works alone:

* `page.console` is reset after every swap, so it means "this screen activated a
  console". A MORPHED console never sets it.
* `console_tabs` is consumed by drawing, so it is per build too. A morphed console
  declares its back tab; the start screen, console select and the results screen
  declare nothing.

CONSOLE_TYPE is deliberately NOT the test, and `test_console_select_is_not_a_console`
is the reason: it is sticky, so a client that has ever sat at a console still reports
one from the results screen - and console select sets it outright.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.mast_sbs.maststorypage import StoryPage, TabControl
from sbs_utils.pages.layout.icon import Icon
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.agent import Agent

CID = 43


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page=None):
        self.jumped = []
        self.main = _FakeMain(page)

    def jump(self, label):
        self.jumped.append(label)

    def tick_in_context(self):
        pass

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s

    def get_variable(self, name, default=None):
        return default

    def set_variable(self, name, value):
        pass


class EpaddScopeBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        self._saved = dict(GuiTabDecoratorLabel.all)
        GuiTabDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all["epadd"] = "label_epadd"
        self.page = StoryPage()
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        self.page.console = ""
        FrameContext.page = None

    def tearDown(self):
        GuiTabDecoratorLabel.all.clear()
        GuiTabDecoratorLabel.all.update(self._saved)
        FrameContext.page = None
        FrameContext.context = None

    def declare(self, names=(), back=None):
        """What a build leaves behind. `gui_tab_back` enables the back tab as well as
        naming it, and the strip only draws a tab that has a route."""
        names = list(names)
        if back is not None and back not in names:
            names.append(back)
        for name in names:
            GuiTabDecoratorLabel.all[name] = "label_%s" % name
        set_inventory_value(CID, "console_tabs", {n: True for n in names})
        if back is not None:
            set_inventory_value(CID, "__back_tab__", back)

    def build(self):
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        return list(self.page.pending_layouts[-1].rows[0].columns)

    def padd_drawn(self):
        """The PADD is its own region beside the tab row, so it is found on the
        page rather than among the row's columns."""
        self.build()
        return getattr(self.page, "identity_badge", None) is not None


class TestTheScreensThatShouldNotHaveIt(EpaddScopeBase):
    def test_the_start_screen_is_not_a_console(self):
        """No console activated, no tabs declared, and the client has never sat
        anywhere - the state before anyone picks a station."""
        self.declare()
        self.assertFalse(self.padd_drawn())

    def test_console_select_is_not_a_console(self):
        """The case that rules CONSOLE_TYPE out as the test.

        `common_console_select.mast` calls `gui_console_enter(client_id,
        CONSOLE_SELECT)`, which WRITES CONSOLE_TYPE - so a screen that is emphatically
        not a console reports one. It declares no console tabs and activates no
        console, which is what actually separates it.
        """
        set_inventory_value(CID, "CONSOLE_TYPE", "select_console")
        self.declare()
        self.assertFalse(self.padd_drawn())

    def test_the_results_screen_is_not_a_console(self):
        """CONSOLE_TYPE is sticky - nothing clears it when a client leaves a console -
        so on the end-of-game screen it still names the station the player last sat
        at. `game_results.mast` declares no tabs and activates no console."""
        set_inventory_value(CID, "CONSOLE_TYPE", "engineering")
        self.declare()
        self.assertFalse(self.padd_drawn())

    def test_the_main_screen_is_not_a_station(self):
        """It is the whole room's view. Named in the report explicitly, and it DOES
        activate a console, so only the main-screen test excludes it."""
        self.page.console = "mainscreen"
        self.declare(["help"], back="engineering")
        self.assertFalse(self.padd_drawn())

    def test_a_morphed_main_screen_is_excluded_too(self):
        """A main screen entered through the door reports itself by role, not name."""
        from sbs_utils.procedural.roles import add_role, remove_role
        add_role(CID, "mainscreen")
        self.addCleanup(remove_role, CID, "mainscreen")
        self.declare(["help"], back="engineering")
        self.assertFalse(self.padd_drawn())

    def test_no_badge_either(self):
        """The button and the badge are one decision, so the results screen gets
        neither. They used to be two, which is why the main screen drew a button with
        no badge under it."""
        set_inventory_value(CID, "CONSOLE_TYPE", "engineering")
        self.declare()
        self.build()
        self.assertIsNone(getattr(self.page, "identity_badge", None))


class TestTheScreensThatShould(EpaddScopeBase):
    def test_a_bridge_console_still_gets_it(self):
        """The guard must not be so broad it takes the PADD off the bridge."""
        self.page.console = "normal_engi"
        self.declare(["help", "cargo"], back="engineering")
        self.assertTrue(self.padd_drawn())

    def test_a_morphed_console_still_gets_it(self):
        """The away console is entered with `gui_console_enter` and no `@console`
        label, so it never sets `page.console` - and carrying the PADD down is the
        whole point of it. It declares a back tab, which is what saves it."""
        set_inventory_value(CID, "CONSOLE_TYPE", "away")
        self.declare(back="select_console")
        self.assertTrue(self.padd_drawn())

    def test_a_console_that_declared_only_a_back_tab_gets_it(self):
        self.page.console = "normal_sci"
        self.declare(back="science")
        self.assertTrue(self.padd_drawn())


class TestModeOffIsStillUntouched(EpaddScopeBase):
    def test_a_console_draws_its_classic_strip(self):
        self.page.console = "normal_engi"
        self.declare(["help", "cargo"], back="engineering")
        labels = sorted(getattr(i, "click_text", None)
                        for i in self.build() if isinstance(i, TabControl))
        self.assertEqual(labels, ["cargo", "engineering", "help"])


if __name__ == "__main__":
    unittest.main()
