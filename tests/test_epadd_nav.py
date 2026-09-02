"""The PADD knows where it is.

Opening an app used to be `task.jump(label)` and nothing else - the same call a tab
click makes - so the PADD had no idea it was open, and its Back had to be reconstructed
from tab state. That is why "clicking an app runs home again" and "Back takes several
presses" were possible at all.

The model these tests pin:

* home is the BOTTOM of the stack, not an entry on it. Opening the shell clears.
* the status area goes home, so an app needs no Back of its own.
* the bar's single Back pops one level INSIDE the PADD, and at depth 1 means "leave" -
  which is the "single tab to go BACK to where it was in the tabs" behavior.
* arriving at any tab forgets the trail, so re-entering the PADD starts at home.

The depth-2 cases are ahead of the shipped screens: nothing drills down today except
the dev tools, which still nest with tabs. They are here because the stack exists for
that shape and an untested stack is a stack that will be wrong when it is first used.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.procedural.gui.console_tab import gui_tab_activate
from sbs_utils.procedural.gui.epadd import (
    gui_app_back, gui_app_depth, gui_app_nav_reset, gui_app_open)

CID = 81


class _Task:
    def __init__(self):
        self.jumped = []

    def jump(self, label):
        self.jumped.append(label)

    def tick_in_context(self):
        pass


class _Page:
    def __init__(self, client_id):
        self.client_id = client_id
        self.console = ""
        self.gui_task = _Task()


class NavBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        FrameContext.task = None
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        self._saved = dict(GuiAppDecoratorLabel.all)
        GuiAppDecoratorLabel.all.clear()
        for name in ("epadd", "cargo", "fabricate", "debug", "mast"):
            GuiAppDecoratorLabel.all[name] = "label_%s" % name
        self.page = _Page(CID)
        FrameContext.page = self.page

    def tearDown(self):
        GuiAppDecoratorLabel.all.clear()
        GuiAppDecoratorLabel.all.update(self._saved)
        FrameContext.page = None
        FrameContext.context = None

    def jumped(self):
        return list(self.page.gui_task.jumped)


class TestDepth(NavBase):
    def test_home_is_depth_zero(self):
        gui_app_open("epadd")
        self.assertEqual(gui_app_depth(CID), 0)

    def test_an_app_is_depth_one(self):
        gui_app_open("cargo")
        self.assertEqual(gui_app_depth(CID), 1)

    def test_opening_the_shell_clears_the_trail(self):
        """Home is the bottom, so going home is a reset rather than another entry."""
        gui_app_open("cargo")
        gui_app_open("epadd")
        self.assertEqual(gui_app_depth(CID), 0)

    def test_reopening_the_same_app_is_not_depth(self):
        """A repaint that re-opens the current app must not stack it."""
        gui_app_open("cargo")
        gui_app_open("cargo")
        self.assertEqual(gui_app_depth(CID), 1)

    def test_a_drill_down_stacks(self):
        gui_app_open("debug")
        gui_app_open("mast")
        self.assertEqual(gui_app_depth(CID), 2)


class TestBack(NavBase):
    def test_AT_DEPTH_ONE_THERE_IS_NOWHERE_TO_GO_BACK_TO(self):
        """None is the caller's cue to leave the PADD entirely - which is what the
        bar's single Back does, and what the user asked for."""
        gui_app_open("cargo")
        self.assertIsNone(gui_app_back(CID))

    def test_home_is_not_a_back_destination(self):
        """The status area goes home. If Back went there too, an app would have two
        ways up and the bar's Back would stop meaning "out"."""
        gui_app_open("cargo")
        self.page.gui_task.jumped.clear()
        gui_app_back(CID)
        self.assertEqual(self.jumped(), [])

    def test_at_depth_two_it_pops_to_the_app_underneath(self):
        gui_app_open("debug")
        gui_app_open("mast")
        self.page.gui_task.jumped.clear()
        self.assertEqual(gui_app_back(CID), "debug")
        self.assertEqual(self.jumped(), ["label_debug"])
        self.assertEqual(gui_app_depth(CID), 1)

    def test_and_then_the_next_press_leaves(self):
        gui_app_open("debug")
        gui_app_open("mast")
        gui_app_back(CID)
        self.assertIsNone(gui_app_back(CID))

    def test_back_at_home_does_nothing(self):
        gui_app_open("epadd")
        self.assertIsNone(gui_app_back(CID))


class TestLeavingForgetsTheTrail(NavBase):
    def test_arriving_at_a_tab_resets_it(self):
        """Re-entering the PADD starts at home, not wherever you left off two consoles
        ago. Done in `gui_tab_activate` so no tab has to know the PADD exists."""
        gui_app_open("cargo")
        gui_tab_activate("helm")
        self.assertEqual(gui_app_depth(CID), 0)

    def test_and_it_can_be_reset_outright(self):
        gui_app_open("cargo")
        gui_app_nav_reset(CID)
        self.assertEqual(gui_app_depth(CID), 0)

    def test_the_trail_is_per_client(self):
        other = Agent()
        other.id = CID + 1
        other.add()
        gui_app_open("cargo")
        self.assertEqual(gui_app_depth(CID), 1)
        self.assertEqual(gui_app_depth(CID + 1), 0)


if __name__ == "__main__":
    unittest.main()
