"""Back, as the PADD's chrome means it.

Reported from the Gamma with a Q playtest: "Once on the ePADD, clicking Back to the
console is inconsistent", and later "reusing the Tab's back button is not working... the
current system still breaks the historic tab back".

Both are the same mistake from opposite ends. The PADD's Back was a button on the
CONSOLE'S TAB BAR, so it inherited everything about tabs - a route's `if` (which is what
stranded the away console, whose route is deliberately gated off while ePADD owns away),
the need for a route to exist at all, and a slot on a strip it does not own. And
overriding that button's behaviour broke the bar's own back for everyone else.

So the PADD owns its navigation now. `gui_app_go_back` is the chrome's control:

* one screen back through the PADD's own history, and
* at the bottom - home - it leaves, returning the console to the tab it came from.

The tab bar is not involved at any point, which is why these tests drive the function
rather than reading the strip. `test_the_strip_is_untouched` is the one that pins the
report: the bar's back button must be exactly what it would have been.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast_sbs.maststorypage import StoryPage, TabControl
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.gui.console_tab import gui_app_activate, gui_tab_activate
from sbs_utils.procedural.gui.epadd import (
    gui_app_depth, gui_app_go_back, gui_app_open)
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.spaceobject import SpaceObject

CID = 71


class _FakeGuiTask:
    def __init__(self, page=None):
        self.jumped = []
        self.main = type("M", (), {"page": page})()

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

    def eval_code_checked(self, code):
        return True


class _ConditionFalse(GuiTabDecoratorLabel):
    """`//gui/tab/away if not gui_app_mode_is_on()`, back when that existed."""

    def __init__(self, name):
        self.name = name

    def test(self, task):
        return False


class BackBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        FrameContext.task = None
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        self._tabs = dict(GuiTabDecoratorLabel.all)
        self._apps = dict(GuiAppDecoratorLabel.all)
        GuiTabDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all.clear()
        for name in ("epadd", "cargo", "debug", "mast"):
            GuiAppDecoratorLabel.all[name] = "label_%s" % name
        self.page = StoryPage()
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        self.page.console = ""
        FrameContext.page = self.page

    def tearDown(self):
        GuiTabDecoratorLabel.all.clear()
        GuiTabDecoratorLabel.all.update(self._tabs)
        GuiAppDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all.update(self._apps)
        FrameContext.page = None
        FrameContext.context = None

    def tab(self, name, condition_false=False):
        GuiTabDecoratorLabel.all[name] = (_ConditionFalse(name) if condition_false
                                          else "label_%s" % name)

    def jumped(self):
        return list(self.page.gui_task.jumped)


class TestBackInsideThePadd(BackBase):
    def test_from_an_app_it_goes_home(self):
        self.tab("helm")
        gui_tab_activate("helm")
        gui_app_open("epadd")
        gui_app_open("cargo")
        self.page.gui_task.jumped.clear()
        self.assertTrue(gui_app_go_back(CID))
        self.assertEqual(self.jumped(), ["label_epadd"])

    def test_from_a_screen_that_is_not_a_tile_it_goes_to_what_opened_it(self):
        """`mast` is an app route nobody registered - reachable from Debug, never on
        the home grid."""
        self.tab("helm")
        gui_tab_activate("helm")
        gui_app_open("epadd")
        gui_app_open("debug")
        gui_app_open("mast")
        self.page.gui_task.jumped.clear()
        self.assertTrue(gui_app_go_back(CID))
        self.assertEqual(self.jumped(), ["label_debug"])


class TestBackAtHomeLeaves(BackBase):
    def test_IT_RETURNS_TO_THE_TAB_YOU_CAME_FROM(self):
        """The reported behaviour, now owned by the PADD instead of borrowed from the
        bar. An app route never writes `__active_tab__`, so Helm is still recorded."""
        self.tab("helm")
        gui_tab_activate("helm")
        gui_app_open("epadd")
        self.page.gui_task.jumped.clear()
        self.assertTrue(gui_app_go_back(CID))
        self.assertEqual(self.jumped(), ["label_helm"])
        self.assertEqual(gui_app_depth(CID), 0)

    def test_it_is_the_ACTIVE_tab_not_the_console_default(self):
        self.tab("helm")
        self.tab("weapons")
        gui_tab_activate("helm")
        gui_tab_activate("weapons")
        set_inventory_value(CID, "CONSOLE_TYPE", "helm")
        gui_app_open("epadd")
        self.page.gui_task.jumped.clear()
        gui_app_go_back(CID)
        self.assertEqual(self.jumped(), ["label_weapons"])

    def test_THE_AWAY_CONSOLE_IS_NOT_STRANDED(self):
        """The shipped case that started this. Away's tab route was condition-gated
        off while ePADD owned away - correct as a tab - and the PADD's Back used to
        inherit that condition and vanish. It no longer asks the route anything."""
        self.tab("away", condition_false=True)
        gui_tab_activate("away")
        gui_app_open("epadd")
        self.page.gui_task.jumped.clear()
        self.assertTrue(gui_app_go_back(CID))
        self.assertEqual(self.jumped(),
                         [GuiTabDecoratorLabel.all["away"]],
                         "the condition is not asked - you came from there")

    def test_walking_all_the_way_out_takes_one_press_per_screen(self):
        self.tab("helm")
        gui_tab_activate("helm")
        gui_app_open("epadd")
        gui_app_open("debug")
        gui_app_open("mast")
        self.page.gui_task.jumped.clear()
        for _ in range(3):
            gui_app_go_back(CID)
        self.assertEqual(self.jumped(),
                         ["label_debug", "label_epadd", "label_helm"])


class TestTheTabBarIsNotInvolved(BackBase):
    def strip(self, declared=()):
        set_inventory_value(CID, "console_tabs", {n: True for n in declared})
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        padd = getattr(self.page, "identity_badge", None)
        cols = []
        for layout in self.page.pending_layouts:
            if layout is not padd and getattr(layout, "rows", None):
                cols = list(layout.rows[0].columns)
        return [t for t in (getattr(c, "click_text", None)
                            for c in cols if isinstance(c, TabControl)) if t]

    def test_the_bar_keeps_its_back_to_console(self):
        """Two backs, and they mean different things. The chrome's arrow walks the
        PADD's history; this one is the bar's ordinary back-to-console, rightmost as
        always, so leaving is one press from any depth.

        A PADD screen declares no tabs, so without the strip supplying the destination
        the button would simply be absent - the console's own build set it and drawing
        consumed it.
        """
        self.tab("helm")
        gui_tab_activate("helm")
        gui_app_activate("cargo")
        self.assertEqual(self.strip(), ["helm"])

    def test_AND_IT_IS_NOT_OVERRIDDEN(self):
        """The second half of the report. Supplying the button's DESTINATION is fine;
        replacing its BEHAVIOUR with PADD semantics is what broke the bar's own back
        for everything else, so it stays a plain TabControl."""
        self.tab("helm")
        gui_tab_activate("helm")
        gui_app_activate("cargo")
        set_inventory_value(CID, "console_tabs", {})
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        padd = getattr(self.page, "identity_badge", None)
        for layout in self.page.pending_layouts:
            if layout is padd or not getattr(layout, "rows", None):
                continue
            for col in layout.rows[0].columns:
                if isinstance(col, TabControl):
                    self.assertIs(type(col), TabControl,
                                  "the bar's back must not be a PADD subclass")

    def test_a_consoles_own_back_tab_still_works(self):
        """Nothing about an ordinary console's strip changed."""
        self.tab("engineering")
        self.page.console = "normal_engi"
        set_inventory_value(CID, "__back_tab__", "engineering")
        self.assertEqual(self.strip(declared=("engineering",)), ["engineering"])

    def test_the_status_region_is_still_the_way_in(self):
        """It stays on the strip on a console - that is the door to the PADD."""
        self.tab("engineering")
        self.page.console = "normal_engi"
        self.strip(declared=("engineering",))
        self.assertIsNotNone(getattr(self.page, "identity_badge", None))


if __name__ == "__main__":
    unittest.main()
