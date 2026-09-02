"""`//gui/app` - a PADD screen, as against `//gui/tab` - a destination on the bar.

Apps used to BE tabs, and one route kind doing two jobs is what produced every symptom
reported from the Gamma with a Q playtest:

* Back inherited a tab's `if`. `//gui/tab/away if not gui_app_mode_is_on()` correctly
  hid away as a tab while ePADD owned it, and deleted the way back to the away console.
* Back vanished when a console had no `//gui/tab/<name>` route at all.
* The PADD competed for slots on the bar, because it was a tab among tabs.

A tab's condition answers "may this be offered on the bar"; an app's answers "is this
app available right now". Those are different questions, so they are different kinds.

The activation split is the load-bearing half: an app route writes `__active_app__` and
NEVER touches `__active_tab__`, so the tab a player was on when they opened the PADD is
still recorded - which is what the PADD's single Back returns to, with nothing having to
capture it. `gui_tab_activate` clears `__active_app__` in the other direction, so
arriving at any tab ends the PADD state without the tab knowing the PADD exists.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401 - registers the node kinds
from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.mast_sbs.story_nodes.route_label import RouteDecoratorLabel
from sbs_utils.procedural.gui.console_tab import (
    gui_app_activate, gui_app_get_active, gui_tab_activate, gui_tab_get_active)
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value

CID = 61


class TestTheRuleItself(unittest.TestCase):
    def test_it_matches_a_gui_app_route(self):
        m = GuiAppDecoratorLabel.rule.match("//gui/app/cargo")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("path"), "cargo")

    def test_it_carries_a_condition(self):
        m = GuiAppDecoratorLabel.rule.match("//gui/app/casino if CASINO_ENABLED")
        self.assertIsNotNone(m)
        self.assertEqual(m.group("path"), "casino")

    def test_it_does_not_match_a_tab(self):
        self.assertIsNone(GuiAppDecoratorLabel.rule.match("//gui/tab/helm"))

    def test_and_the_tab_rule_does_not_match_an_app(self):
        self.assertIsNone(GuiTabDecoratorLabel.rule.match("//gui/app/cargo"))

    def test_IT_IS_REGISTERED_AHEAD_OF_THE_GENERIC_ROUTE(self):
        """The whole reason `story_nodes/__init__` imports it after `route_label`.

        `@mast_node(append=False)` inserts at the FRONT and the compiler takes the first
        match, so registered later means matched earlier. Get this wrong and
        `//gui/app/x` is swallowed by `RouteDecoratorLabel`'s `case ["gui", *b]` and
        silently becomes a navigation route instead.
        """
        names = [c.__name__ for c in MastNode.nodes]
        self.assertIn("GuiAppDecoratorLabel", names)
        self.assertLess(names.index("GuiAppDecoratorLabel"),
                        names.index("RouteDecoratorLabel"))


class TestRegistration(unittest.TestCase):
    def setUp(self):
        self._saved = dict(GuiAppDecoratorLabel.all)
        GuiAppDecoratorLabel.all.clear()

    def tearDown(self):
        GuiAppDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all.update(self._saved)

    def test_declaring_one_registers_it_by_path(self):
        label = GuiAppDecoratorLabel("cargo")
        self.assertIs(GuiAppDecoratorLabel.all["cargo"], label)

    def test_the_label_name_says_it_is_an_app(self):
        """Mangled per declaration, so two of the same path cannot collide as labels."""
        self.assertTrue(GuiAppDecoratorLabel("cargo").name.startswith("gui/app/cargo/"))

    def test_apps_and_tabs_keep_separate_tables(self):
        """A name may be an app OR a tab; the two tables never see each other."""
        GuiAppDecoratorLabel("debug")
        self.assertIn("debug", GuiAppDecoratorLabel.all)
        self.assertNotIn("debug", GuiTabDecoratorLabel.all)

    def test_CLEAR_IS_WIRED_TO_THE_MISSION_RESET(self):
        """An unregistered table carries two generations of routes across an in-process
        reload, and opening an app then runs a label from the dead compile."""
        import inspect
        from sbs_utils import handlerhooks
        src = inspect.getsource(handlerhooks.reset_mission_state)
        self.assertIn("GuiAppDecoratorLabel.clear()", src)

    def test_clear_empties_it(self):
        GuiAppDecoratorLabel("cargo")
        GuiAppDecoratorLabel.clear()
        self.assertEqual(GuiAppDecoratorLabel.all, {})


class _Page:
    """Just enough page for `_tab_client_id`, which asks the PAGE whose strip it is."""

    def __init__(self, client_id):
        self.client_id = client_id


class TestActivation(unittest.TestCase):
    """The asymmetry that makes the return point work."""

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        FrameContext.page = _Page(CID)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def test_an_app_does_not_disturb_the_active_tab(self):
        """The point. Opening the PADD from Helm must leave Helm recorded, or Back has
        nowhere to go."""
        gui_tab_activate("helm")
        gui_app_activate("epadd")
        gui_app_activate("cargo")
        self.assertEqual(gui_tab_get_active(), "helm")
        self.assertEqual(gui_app_get_active(CID), "cargo")

    def test_arriving_at_a_tab_ends_the_padd(self):
        """The other direction, and it is done HERE so no tab has to know the PADD
        exists - otherwise the strip would go on drawing the PADD's bar over a
        console."""
        gui_app_activate("cargo")
        gui_tab_activate("weapons")
        self.assertEqual(gui_app_get_active(CID), "")
        self.assertEqual(gui_tab_get_active(), "weapons")

    def test_not_in_the_padd_by_default(self):
        self.assertEqual(gui_app_get_active(CID), "")

    def test_it_answers_for_the_client_it_is_asked_about(self):
        """The page asks while drawing, and the ambient page is not reliably the one
        being built - the same distinction `epadd._client_id` documents."""
        other = Agent()
        other.id = CID + 1
        other.add()
        set_inventory_value(CID, "__active_app__", "cargo")
        self.assertEqual(gui_app_get_active(CID), "cargo")
        self.assertEqual(gui_app_get_active(CID + 1), "")


if __name__ == "__main__":
    unittest.main()
