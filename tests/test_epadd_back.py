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


class TestTheClickTagDoesNotMoveBetweenBuilds(BackBase):
    """A tab's click tag is keyed by its NAME, not by the build counter.

    `get_tag()` is a build-order ordinal that jumps ~2100 every rebuild, so a fresh
    click tag per build asked the engine for a NEW click region each time and left the
    previous one live. A press could then be answered by a region belonging to a build
    that no longer exists, and do nothing.

    Measured in a real session: Back presses arriving as `9483` and `70583` while the
    current build was at `15784` and `76884` - about three builds stale, each a press
    that did nothing. That is the reported "Back takes several presses"; the ones that
    worked were the ones that happened to land on the current build.
    """

    def build_back(self):
        self.tab("engineering")
        gui_tab_back("engineering")
        cols = self.build()
        return next(c for c in cols if getattr(c, "click_text", None) == "engineering")

    def test_the_same_tab_keeps_the_same_click_tag(self):
        first = self.build_back().click_tag
        second = self.build_back().click_tag       # a second build of the same strip
        self.assertEqual(first, second)

    def test_it_is_not_a_build_counter(self):
        """A bare ordinal is what moved. The name is what does not."""
        tag = str(self.build_back().click_tag)
        self.assertFalse(tag.isdigit(), tag)
        self.assertIn("engineering", tag)

    def test_two_tabs_still_differ(self):
        """Stable must not mean shared - a tab appears once in a strip, so its name is
        unique within a build."""
        self.tab("engineering")
        self.tab("science")
        gui_tab_back("engineering")
        set_inventory_value(CID, "console_tabs",
                            {"engineering": True, "science": True})
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        padd = getattr(self.page, "identity_badge", None)
        tags = []
        for layout in self.page.pending_layouts:
            if layout is padd or not getattr(layout, "rows", None):
                continue
            for c in layout.rows[0].columns:
                if isinstance(c, TabControl):
                    tags.append(c.click_tag)
        self.assertEqual(len(tags), len(set(tags)), tags)


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
