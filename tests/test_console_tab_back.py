"""The Back tab is a return path, not an offer.

Reported from the Gamma with a Q playtest: "Once on the ePADD, clicking Back to the
console is inconsistent."

It was. The strip drew the back tab exactly like any other tab, which meant applying the
route's own `if` to it - and a tab's condition answers "may this be picked from here",
which is a different question from "where did you come from". You demonstrably came from
there.

The shipped case is the away console. Its route reads

    //gui/tab/away if not gui_app_mode_is_on()

which correctly hides away as a TAB while ePADD is on, because away is an app there - and
also deleted the way back to it. So Back worked from the six standard consoles, whose
routes carry no condition, and silently did not exist from the away console. Hence
"inconsistent".

The second half is a mission bug rather than a library one, but it used to be equally
silent: a back tab naming a console with no `//gui/tab/<name>` route at all has nothing
to jump to, and the button simply was not drawn.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.mast_sbs.maststorypage import StoryPage, TabControl
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.agent import Agent

CID = 52


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


class _ConditionFalse(GuiTabDecoratorLabel):
    """A route whose own `if` is false right now - `//gui/tab/away` in ePADD mode."""

    def __init__(self, name):
        self.name = name

    def test(self, task):
        return False


class BackTabBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        self._saved = dict(GuiTabDecoratorLabel.all)
        GuiTabDecoratorLabel.all.clear()
        self.page = StoryPage()
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        self.page.console = "normal_engi"
        FrameContext.page = None

    def tearDown(self):
        GuiTabDecoratorLabel.all.clear()
        GuiTabDecoratorLabel.all.update(self._saved)
        FrameContext.page = None
        FrameContext.context = None

    def route(self, name, condition_false=False):
        GuiTabDecoratorLabel.all[name] = (_ConditionFalse(name) if condition_false
                                          else "label_%s" % name)

    def build_with_back(self, back, extra=()):
        tabs = {back: True} if back else {}
        for e in extra:
            tabs[e] = True
        set_inventory_value(CID, "console_tabs", tabs)
        set_inventory_value(CID, "__back_tab__", back)
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        cols = self.page.pending_layouts[-1].rows[0].columns
        return [t for t in (getattr(c, "click_text", None)
                            for c in cols if isinstance(c, TabControl)) if t]


class TestTheBackTabIgnoresItsRouteCondition(BackTabBase):
    def test_an_unconditional_route_still_works(self):
        """The case that always worked, so the fix is measured against it."""
        self.route("engineering")
        self.assertIn("engineering", self.build_with_back("engineering"))

    def test_A_FALSE_CONDITION_NO_LONGER_DELETES_THE_WAY_BACK(self):
        """The away console, and the whole report. Its route is condition-gated off in
        ePADD mode - correctly, as a TAB - and that used to strand the console."""
        self.route("away", condition_false=True)
        self.assertIn("away", self.build_with_back("away"))

    def test_but_a_false_condition_still_hides_it_as_an_ordinary_tab(self):
        """The condition is not being ignored in general - only for the tab you came
        from. Away must still not be OFFERED while ePADD owns it."""
        self.route("engineering")
        self.route("away", condition_false=True)
        shown = self.build_with_back("engineering", extra=("away",))
        self.assertIn("engineering", shown)
        self.assertNotIn("away", shown)


class TestARoutelessBackTabSaysSo(BackTabBase):
    def _logged(self, back):
        """Patched on the MODULE, not on `procedural.execution`.

        `maststorypage` does `from ..procedural.execution import log` at import, so the
        name is already bound there and replacing the original is not seen.
        """
        import sbs_utils.mast_sbs.maststorypage as MSP
        out = []
        orig = MSP.log
        MSP.log = lambda msg, *a, **k: out.append(msg)
        try:
            self.build_with_back(back)
        finally:
            MSP.log = orig
        return out

    def test_it_is_reported_by_name(self):
        """A mission's own console has to declare `//gui/tab/<name>` too. Nothing can
        be drawn without it - but the gap is named rather than left as a console you
        cannot leave."""
        msgs = self._logged("director")
        self.assertTrue(any("director" in m for m in msgs), msgs)

    def test_and_only_once(self):
        """It runs on every build of every console, so an unguarded log is the same
        line several times a second."""
        self.route("engineering")
        first = self._logged("director")
        second = self._logged("director")
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_a_back_tab_that_resolves_says_nothing(self):
        self.route("engineering")
        self.assertEqual(self._logged("engineering"), [])


if __name__ == "__main__":
    unittest.main()
