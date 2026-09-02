"""The PADD knows where it is.

Opening an app used to be `task.jump(label)` and nothing else - the same call a tab
click makes - so the PADD had no idea it was open, and its Back had to be reconstructed
from tab state. That is why "clicking an app runs home again" and "Back takes several
presses" were possible at all.

The model these tests pin:

* HOME IS AN ENTRY, like a browser's first page. Back from an app is home; Back from
  home leaves the PADD. That is what makes a separate HOME button redundant.
* the PADD's chrome owns Back. The tab bar is not involved, so the bar's own back
  button keeps working the way it always did.
* arriving at any tab forgets the trail, so re-entering the PADD starts at home.

A screen that is not a tile is just an app route nobody registered - `gui_app_list`
reads the registry, not the route table. There is no separate kind for it.
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
    def test_not_in_the_padd_is_depth_zero(self):
        self.assertEqual(gui_app_depth(CID), 0)

    def test_HOME_IS_AN_ENTRY(self):
        """Browser semantics, and it is what makes a HOME button redundant: with a
        history of [home, app], Back from the app IS home."""
        gui_app_open("epadd")
        self.assertEqual(gui_app_depth(CID), 1)

    def test_an_app_opened_from_home_is_depth_two(self):
        gui_app_open("epadd")
        gui_app_open("cargo")
        self.assertEqual(gui_app_depth(CID), 2)

    def test_reopening_the_same_screen_is_not_depth(self):
        """A repaint that re-opens the current screen must not stack it."""
        gui_app_open("cargo")
        gui_app_open("cargo")
        self.assertEqual(gui_app_depth(CID), 1)

    def test_a_drill_down_stacks(self):
        """`mast` is an app route with no registration - reachable from Debug,
        never a tile on the home grid. That is all a "page" ever needed to be."""
        gui_app_open("epadd")
        gui_app_open("debug")
        gui_app_open("mast")
        self.assertEqual(gui_app_depth(CID), 3)


class TestBack(NavBase):
    def test_BACK_FROM_AN_APP_IS_HOME(self):
        """Which is the whole reason the HOME button was redundant."""
        gui_app_open("epadd")
        gui_app_open("cargo")
        self.page.gui_task.jumped.clear()
        self.assertEqual(gui_app_back(CID), "epadd")
        self.assertEqual(self.jumped(), ["label_epadd"])
        self.assertEqual(gui_app_depth(CID), 1)

    def test_BACK_AT_HOME_LEAVES_THE_PADD(self):
        """None is the caller's cue to leave - the chrome then returns the console to
        the tab it came from."""
        gui_app_open("epadd")
        self.assertIsNone(gui_app_back(CID))

    def test_a_page_pops_to_the_app_that_opened_it(self):
        gui_app_open("epadd")
        gui_app_open("debug")
        gui_app_open("mast")
        self.page.gui_task.jumped.clear()
        self.assertEqual(gui_app_back(CID), "debug")
        self.assertEqual(self.jumped(), ["label_debug"])

    def test_and_the_presses_after_it_walk_all_the_way_out(self):
        gui_app_open("epadd")
        gui_app_open("debug")
        gui_app_open("mast")
        self.assertEqual(gui_app_back(CID), "debug")
        self.assertEqual(gui_app_back(CID), "epadd")
        self.assertIsNone(gui_app_back(CID))

    def test_back_outside_the_padd_does_nothing(self):
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
