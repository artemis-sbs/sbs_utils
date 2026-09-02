"""One gui tab, and it is the way back to the console.

Reported across three rounds of the Gamma with a Q playtest: "clicking Back to the
console is inconsistent", then "reusing the Tab's back button is not working", then "the
current system still breaks the historic tab back".

All three were the same mistake. Every PADD screen used to declare
`gui_tab_back(CONSOLE_SELECT)` - one tab, back to the console, exactly like any other
screen - and that line was deleted on the theory that "apps have no back". What replaced
it was the strip SYNTHESISING a back entry while the PADD was open, which meant the PADD
reaching into the tab system's per-build state, and that is what kept breaking the bar's
own back button.

So the property is now the absence of cleverness: the PADD adds nothing to the strip and
changes nothing about it. It declares a back tab; the bar draws it the way it always has.
`test_it_is_a_plain_TabControl` is the guard against the subclass creeping back.

Navigating INSIDE the PADD is HOME on the bar - see `gui_app_chrome`. There is no PADD
history, no depth, and no second Back.
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
from sbs_utils.procedural.gui.console_tab import gui_app_activate, gui_tab_back
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
    """A tab route whose own `if` is false right now."""

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

    def build(self):
        """What a PADD screen leaves behind: one back tab, and nothing else."""
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        padd = getattr(self.page, "identity_badge", None)
        cols = []
        for layout in self.page.pending_layouts:
            if layout is not padd and getattr(layout, "rows", None):
                cols = list(layout.rows[0].columns)
        return [c for c in cols if isinstance(c, TabControl)]

    def labels(self):
        return [getattr(c, "click_text", None) for c in self.build()]


class TestOneTab(BackBase):
    def test_a_padd_screen_declares_one_and_the_bar_draws_one(self):
        self.tab("engineering")
        gui_app_activate("cargo")
        gui_tab_back("engineering")
        self.assertEqual(self.labels(), ["engineering"])

    def test_IT_IS_A_PLAIN_TabControl(self):
        """The guard. Supplying the button's destination is fine; replacing its
        BEHAVIOUR with PADD semantics is what broke the bar's back for everything
        else, and a subclass here is how that comes back."""
        self.tab("engineering")
        gui_app_activate("cargo")
        gui_tab_back("engineering")
        for c in self.build():
            self.assertIs(type(c), TabControl)

    def test_the_same_at_every_depth(self):
        """Home, an app, a sub-app - the bar is the same one tab throughout, because
        each screen declares it and nothing accumulates."""
        self.tab("engineering")
        for screen in ("epadd", "debug", "mast"):
            gui_app_activate(screen)
            gui_tab_back("engineering")
            self.assertEqual(self.labels(), ["engineering"], screen)

    def test_a_condition_on_the_route_is_not_asked(self):
        """The away console. Its tab route is deliberately gated off, and the back tab
        answers "where did you come from", not "may this be picked from here"."""
        self.tab("away", condition_false=True)
        gui_app_activate("cargo")
        gui_tab_back("away")
        self.assertEqual(self.labels(), ["away"])


class TestThePaddAddsNothing(BackBase):
    def test_a_screen_that_declares_no_tab_gets_no_tab(self):
        """The strip does not invent one. It used to synthesise a back entry from the
        active tab whenever the PADD was open, which is the special-casing this whole
        change removed."""
        self.tab("engineering")
        gui_app_activate("cargo")
        self.assertEqual(self.build(), [])

    def test_but_the_status_region_is_still_drawn(self):
        """It is the way IN to the PADD, so it survives on a console."""
        self.tab("engineering")
        self.page.console = "normal_engi"
        gui_tab_back("engineering")
        self.build()
        self.assertIsNotNone(getattr(self.page, "identity_badge", None))


if __name__ == "__main__":
    unittest.main()
