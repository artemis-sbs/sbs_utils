"""`$INFO_PATH` belongs to the INFO panel, not to whichever panel presented last.

`TabbedPanel.present_panel` records which tab is showing in a task variable named
`$INFO_PATH`, and the standard message/log tab functions read that name at TICK
time - once a second, from a variable any panel on the page could have overwritten
since.

That was fine while a console had exactly one tabbed panel. Engineering now builds
a second, private one for its grid column, and without a scope guard the info panel's
tick would read `$ENG_ORDERS`, find no queue by that name, return 0, and 0 means
"this tab is done" - so `set_tab(default_tab)` would bounce the panel back to ship
data every second, from the other side of the screen.

The guard: only the page's own info panel writes the shared name. Every panel still
records its tab on itself as `current_path`.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.pages.widgets.tabbed_panel import TabbedPanel

CID = 77


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)
        self.vars = {}

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


class _Size:
    x = 30
    y = 30


class InfoPathScope(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = CID
        self.task = _FakeGuiTask(self.page)
        self.page.gui_task = self.task
        FrameContext.page = self.page

        from sbs_utils.gui import GuiClient
        client = GuiClient(CID)
        client.page_stack.append(self.page)
        client.gui_task = self.task
        self.client = client

        # Two panels on one page, as Engineering has: the info panel on the left and
        # a private grid panel on the right.
        self.info = TabbedPanel(0, 0, 10, 10, "info$", [], 0, 0, 30)
        self.grid = TabbedPanel(0, 0, 10, 10, "grid$", [], 0, 0, 26)
        self.page.info_panel = self.info

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None
        SpaceObject.clear()

    def present(self, panel, path):
        # show=None: this is about the task variable, not about drawing.
        panel.present_panel(FakeEvent(CID), {"path": path, "show": None}, _Size())

    def test_the_info_panel_owns_the_shared_name(self):
        self.present(self.info, "message")
        self.assertEqual(self.task.get_variable("$INFO_PATH"), "message")

    def test_a_second_panel_does_NOT_overwrite_it(self):
        """The bug this guard exists for: the grid panel presenting after the info
        panel used to leave its own path in the shared variable, and the info panel's
        1Hz tick then read a queue that does not exist."""
        self.present(self.info, "message")
        self.present(self.grid, "eng_orders")
        self.assertEqual(self.task.get_variable("$INFO_PATH"), "message")

    def test_order_does_not_matter(self):
        self.present(self.grid, "eng_systems")
        self.assertIsNone(self.task.get_variable("$INFO_PATH"))
        self.present(self.info, "log")
        self.assertEqual(self.task.get_variable("$INFO_PATH"), "log")

    def test_a_pending_info_panel_counts_as_the_owner(self):
        """During a build the panel is on `pending_info_panel` and has not been
        promoted yet, so the guard has to accept that too - otherwise the info
        panel's own first present would not record its tab."""
        self.page.info_panel = None
        self.page.pending_info_panel = self.info
        self.present(self.info, "ship_data")
        self.assertEqual(self.task.get_variable("$INFO_PATH"), "ship_data")

    def test_every_panel_records_its_own_tab_regardless(self):
        self.present(self.info, "message")
        self.present(self.grid, "eng_orders")
        self.assertEqual(self.info.current_path, "message")
        self.assertEqual(self.grid.current_path, "eng_orders")


if __name__ == "__main__":
    unittest.main()
