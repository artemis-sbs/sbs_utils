"""The PADD's Back returns you to the tab you were on.

Reported from the Gamma with a Q playtest: "Once on the ePADD, clicking Back to the
console is inconsistent."

It was, in two different ways, and both came from apps being tabs:

* Back was a tab pointing at `//gui/tab/<console>`, so it inherited that route's `if`.
  The away console's route is `//gui/tab/away if not gui_app_mode_is_on()` - correct as
  a TAB while ePADD owns away, and it deleted the way back to the away console with it.
* A console with no `//gui/tab/<name>` route at all had its Back silently not drawn.

And a third thing that was never right: every app screen called
`gui_tab_back(CONSOLE_SELECT)`, whose route jumps to `console_selected` - so Back from
an app left the PADD entirely for the bridge console. "App to app" had never worked.

Now an app route writes `__active_app__` and never touches `__active_tab__`, so the tab
that was showing is still recorded and Back goes THERE. These tests drive it: activate a
tab, enter the PADD, open an app, read the strip.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast_sbs.maststorypage import StoryPage, TabControl
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.gui.console_tab import gui_app_activate, gui_tab_activate
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
    """`//gui/tab/away if not gui_app_mode_is_on()`, once ePADD is on."""

    def __init__(self, name):
        self.name = name

    def test(self, task):
        return False


class BackBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        self._tabs = dict(GuiTabDecoratorLabel.all)
        self._apps = dict(GuiAppDecoratorLabel.all)
        GuiTabDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all["epadd"] = "label_epadd"
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

    def app(self, name):
        GuiAppDecoratorLabel.all[name] = "label_%s" % name

    def enter_padd(self, app="cargo"):
        """What actually happens: the app's route runs its injected activate."""
        self.app(app)
        gui_app_activate(app)

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


class TestBackGoesToTheTabYouWereOn(BackBase):
    def test_THE_REPORTED_BUG(self):
        """Helm, then the PADD, then an app. Back says Helm."""
        self.tab("helm")
        gui_tab_activate("helm")
        self.enter_padd()
        self.assertEqual(self.strip(), ["helm"])

    def test_it_is_the_ACTIVE_tab_not_the_console_default(self):
        """You were on Weapons when you opened it, so Back is Weapons - not whatever
        console you happen to be seated at."""
        self.tab("helm")
        self.tab("weapons")
        gui_tab_activate("helm")
        gui_tab_activate("weapons")
        set_inventory_value(CID, "CONSOLE_TYPE", "helm")
        self.enter_padd()
        self.assertEqual(self.strip(), ["weapons"])

    def test_THE_AWAY_CONSOLE_IS_NO_LONGER_STRANDED(self):
        """The shipped case. Away's route is condition-gated off while ePADD owns it -
        correct as a tab - and that used to delete the way back to it."""
        self.tab("away", condition_false=True)
        gui_tab_activate("away")
        self.enter_padd()
        self.assertEqual(self.strip(), ["away"])

    def test_the_padd_is_never_its_own_way_out(self):
        """The shell is an app, so it never lands in `__active_tab__` - but guard it
        anyway, because a Back that reopens the PADD is a trap."""
        self.tab("helm")
        gui_tab_activate("helm")
        self.enter_padd("epadd")
        self.assertEqual(self.strip(), ["helm"])

    def test_it_falls_back_to_the_console_when_no_tab_was_ever_active(self):
        """A console reached without going through a tab route at all."""
        self.tab("engineering")
        set_inventory_value(CID, "CONSOLE_TYPE", "engineering")
        self.enter_padd()
        self.assertEqual(self.strip(), ["engineering"])

    def test_there_is_exactly_ONE_back(self):
        """'A single tab to go BACK to where it was in the tabs'."""
        self.tab("helm")
        gui_tab_activate("helm")
        self.enter_padd()
        self.assertEqual(len(self.strip()), 1)


class TestAppsHaveNoBackOfTheirOwn(BackBase):
    def test_an_app_declaring_nothing_still_gets_the_padd_bar(self):
        """Apps stopped calling `gui_tab_back`, so a build declares no tabs at all -
        and the status region must survive that, since it is the way home."""
        self.tab("helm")
        gui_tab_activate("helm")
        self.enter_padd()
        self.strip()
        self.assertIsNotNone(getattr(self.page, "identity_badge", None))

    def test_an_apps_OWN_tabs_still_draw(self):
        """The dev drill-down: `debug` is an app that enables `mast` and `brain`, and
        those are meant to be on the bar beside Back."""
        self.tab("helm")
        self.tab("mast")
        self.tab("brain")
        gui_tab_activate("helm")
        self.enter_padd("debug")
        self.assertEqual(sorted(self.strip(declared=("mast", "brain"))),
                         ["brain", "helm", "mast"])


class TestLeavingThePadd(BackBase):
    def test_arriving_at_a_tab_ends_the_padd_state(self):
        """Otherwise the bar would go on drawing the PADD's over a console."""
        self.tab("helm")
        gui_tab_activate("helm")
        self.enter_padd()
        gui_tab_activate("helm")
        self.page.console = "normal_helm"
        self.strip(declared=("helm",))
        from sbs_utils.procedural.gui.console_tab import gui_app_get_active
        self.assertEqual(gui_app_get_active(CID), "")


if __name__ == "__main__":
    unittest.main()
