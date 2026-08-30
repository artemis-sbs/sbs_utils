"""A listbox row template must build under the task that OWNS the listbox.

Rows are built lazily, at present time, and the presenting context is not always the
one that created the listbox. A comms route runs on the SERVER task and presents under
the SERVER page, so by the time a row is built both `FrameContext.task` and
`FrameContext.page.gui_task` are the server's.

That matters because `gui_input`/`gui_dropdown`/`gui_slider`/`gui_checkbox` stamp
`var_scope_id` with `FrameContext.task`. Under the old behavior a var-bound widget
inside a property-panel row bound to the SERVER task, while `gui_get_variable` reads the
console's own gui_task - so the player's typing was written to one task and read from
another, the reader always saw "", and nothing raised anywhere.

Measured on a real bridge: LegendaryMissions ship-to-ship comms sent nothing at all,
because `prop_message` was always empty at `+ "Send":` and the `!= ""` guard dropped it
in silence. The trace showed the widget stamped 36028797018963970 (the server's task)
while the Send handler read 36028797018964100 (the console's).

An earlier attempt set the row task from `FrameContext.page.gui_task` and did NOT fix
it - in the bad pass that value is itself the server's task. The listbox has to remember
its own task rather than ask the frame, which is what `owner_task` is.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.agent import Agent
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox

CID = 11


class FakeGuiTask:
    """The slice of a GUI task a row build touches."""

    def __init__(self, name):
        self.name = name
        self.vars = {}
        self.inventory = {}
        self.on_change_items = []

    def __repr__(self):
        return f"<task {self.name}>"

    def get_variable(self, k, d=None):
        return self.vars.get(k, d)

    def set_variable(self, k, v):
        self.vars[k] = v

    def get_inventory_value(self, k, d=None):
        return self.inventory.get(k, d)

    def set_inventory_value(self, k, v):
        self.inventory[k] = v


class FakePage:
    def __init__(self, task, client_id):
        self.gui_task = task
        self.client_id = client_id


class FakeGuiAgent:
    def __init__(self, page):
        self.page = page


class TestRowTemplateTask(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        self.sbs = mock_sbs
        FrameContext.aspect_ratios[CID] = Vec3(1024, 768, 0)

        self.console_task = FakeGuiTask("console")
        self.server_task = FakeGuiTask("server")
        self.console_page = FakePage(self.console_task, CID)
        self.server_page = FakePage(self.server_task, 0)
        Agent.all[CID] = FakeGuiAgent(self.console_page)

        # The console's own build: this is where a listbox is created, and the only
        # moment the right answer is on the frame.
        FrameContext.context = Context(mock_sbs.sim, mock_sbs,
                                       FakeEvent(client_id=CID, tag="gui_present"))
        FrameContext.page = self.console_page
        FrameContext.task = self.console_task

    def tearDown(self):
        Agent.all.pop(CID, None)
        FrameContext.context = None
        FrameContext.task = None
        FrameContext.page = None

    def _listbox(self, seen):
        def template(item, **kwargs):
            seen.append(FrameContext.task)
            return None
        return LayoutListbox(0, 0, "lb", ["row"], item_template=template)

    def _present_as_the_server(self):
        """What a comms route leaves on the frame: the server's task and page pinned,
        while the widgets being drawn belong to a console."""
        FrameContext.page = self.server_page
        FrameContext.task = self.server_task

    def test_the_owner_task_is_captured_at_construction(self):
        lb = self._listbox([])
        self.assertIs(lb.owner_task, self.console_task,
                      "the listbox must remember the console that created it")

    def test_a_row_measured_under_the_server_still_builds_as_the_console(self):
        seen = []
        lb = self._listbox(seen)
        self._present_as_the_server()

        lb.calc_max(CID)

        self.assertTrue(seen, "the row template did not run")
        self.assertIs(seen[0], self.console_task,
                      "the row bound to the presenting task, so any var-bound widget "
                      "in it writes where nothing reads")

    def test_the_frame_is_left_exactly_as_it_was_found(self):
        """The swap is restored, including the case where nothing was pinned: the getter
        falls back to page.gui_task while `_task` is None, and pinning it here would
        change what every later caller in the frame sees."""
        lb = self._listbox([])
        FrameContext.page = self.server_page
        FrameContext._task = None

        lb.calc_max(CID)

        self.assertIsNone(FrameContext._task, "an unpinned frame must stay unpinned")
        self.assertIs(FrameContext.page, self.server_page)

        FrameContext.task = self.server_task
        lb.calc_max(CID)
        self.assertIs(FrameContext.task, self.server_task,
                      "a pinned frame must get its own task back")


if __name__ == "__main__":
    unittest.main()
