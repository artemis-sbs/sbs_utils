"""The console tab strip overflows into a menu instead of shrinking (PRM-26).

Reported as "science still can't access the upgrades tab, and adding more tabs made it
worse". The strip never dropped a tab and never scrolled - it divided a FIXED width
(20%..100%) evenly, so more tabs just meant narrower ones:

    4 tabs -> 20.0% each      9 tabs ->  8.9%     18 tabs -> 4.4% (~85px at 1920)

"engineering" needs roughly 130px, and the engine does not clip text - it draws it anyway,
over the neighbouring tab. So every tab was present, clickable, and unreadable, which is
exactly why adding tabs damaged the ones already there.

    python -m unittest tests.test_console_tab_overflow
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.mast_sbs.maststorypage import (
    StoryPage, TabControl, TabOverflow, TAB_MAX_VISIBLE)
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.agent import Agent


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


CID = 42


class TabStripTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        # The strip reads its enabled-tab set from client inventory, which needs an agent
        # to live on.
        self.client = Agent()
        self.client.id = CID
        self.client.add()
        self._saved = dict(GuiTabDecoratorLabel.all)
        GuiTabDecoratorLabel.all.clear()
        self.page = StoryPage()
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        self.page.console = "science"

    def tearDown(self):
        GuiTabDecoratorLabel.all.clear()
        GuiTabDecoratorLabel.all.update(self._saved)
        FrameContext.context = None

    def _strip(self, n, back=None):
        """Register n tabs, build the strip, return its row's items."""
        names = [f"tab{i}" for i in range(n)]
        for name in names:
            GuiTabDecoratorLabel.all[name] = f"label_{name}"
        set_inventory_value(CID, "console_tabs", {name: True for name in names})
        if back is not None:
            set_inventory_value(CID, "__back_tab__", back)
        self.page.pending_layouts = []
        self.page.gui_queue_console_tabs()
        row = self.page.pending_layouts[-1].rows[0]
        return names, list(row.columns)

    def _kinds(self, items):
        return [type(i).__name__ for i in items]

    def test_a_few_tabs_are_all_shown_with_no_menu(self):
        _names, items = self._strip(4)
        self.assertEqual(4, self._kinds(items).count("TabControl"))
        self.assertNotIn("TabOverflow", self._kinds(items))

    def test_exactly_the_limit_still_has_no_menu(self):
        _names, items = self._strip(TAB_MAX_VISIBLE)
        self.assertEqual(TAB_MAX_VISIBLE, self._kinds(items).count("TabControl"))
        self.assertNotIn("TabOverflow", self._kinds(items))

    def test_past_the_limit_the_rest_go_in_a_menu(self):
        n = TAB_MAX_VISIBLE + 5
        names, items = self._strip(n)
        kinds = self._kinds(items)
        self.assertIn("TabOverflow", kinds)
        menu = next(i for i in items if isinstance(i, TabOverflow))
        shown = kinds.count("TabControl")
        self.assertEqual(n, shown + len(menu.labels), "every tab is somewhere")
        self.assertLessEqual(shown + 1, TAB_MAX_VISIBLE,
                             "the visible row never exceeds what fits")

    def test_the_back_tab_is_never_overflowed(self):
        """It is how you leave the screen - it must not hide behind a menu."""
        names, items = self._strip(TAB_MAX_VISIBLE + 5, back="tab0")
        menu = next(i for i in items if isinstance(i, TabOverflow))
        self.assertNotIn("tab0", menu.labels)
        self.assertIn("tab0", [getattr(i, "click_text", None) for i in items])

    def test_choosing_from_the_menu_jumps_like_a_tab(self):
        names, items = self._strip(TAB_MAX_VISIBLE + 5)
        menu = next(i for i in items if isinstance(i, TabOverflow))
        picked = next(iter(menu.labels))
        event = FakeEvent(CID)
        event.sub_tag = menu.tag
        event.value_tag = picked
        menu.on_message(event)
        self.assertEqual([menu.labels[picked]], self.page.gui_task.jumped)

    def test_an_unknown_selection_does_not_jump(self):
        names, items = self._strip(TAB_MAX_VISIBLE + 5)
        menu = next(i for i in items if isinstance(i, TabOverflow))
        event = FakeEvent(CID)
        event.sub_tag = menu.tag
        event.value_tag = "not_a_tab"
        menu.on_message(event)
        self.assertEqual([], self.page.gui_task.jumped)


if __name__ == "__main__":
    unittest.main()
