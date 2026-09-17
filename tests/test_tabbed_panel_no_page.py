"""A tab redraw must not take down the tick phase when the client has no page.

`gui_page_for_client` is documented nullable and really is None for a client with no gui
agent - the SERVER (client 0) among them, since Agent.get(0) is None. present_panel
dereferenced it to merge the sub-page's click tags, so a tab redrawing on such a client
raised out of TickDispatcher.dispatch_tick and took BRAINS AND TIMERS with it:

    AttributeError: 'NoneType' object has no attribute 'tag_map'

The same merge in procedural/gui/overlay.py has always been guarded - the lesson was
learned there and missed here. Rare while only comms traffic grew the log; constant once
the retired toast started feeding it too, which is how it surfaced.

    python -m unittest tests.test_tabbed_panel_no_page
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.gui import GuiClient
from sbs_utils.procedural.gui.gui import gui_page_for_client
from sbs_utils.pages.widgets.tabbed_panel import TabbedPanel


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


CID = 0        # the server: Agent.get(0) is None, so it has no gui page


class TabRedrawWithNoPageTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID))
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = CID
        self.page.gui_task = _FakeGuiTask(self.page)
        FrameContext.page = self.page

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def _panel(self):
        p = TabbedPanel(0, 0, 50, 50, "info", panels=[
            {"path": "log", "icon": 112, "show": lambda cid, l, t, w, h: None,
             "hide": None, "tick": None}])
        p.client_id = CID
        return p

    def test_the_client_really_has_no_page(self):
        """Guards the premise: if this ever starts returning a page, the test below
        stops testing anything."""
        self.assertIsNone(gui_page_for_client(CID))

    def test_presenting_a_tab_does_not_raise(self):
        panel = self._panel()
        panel.present_panel(FakeEvent(CID), panel.panels[0], _IconSize())

    def test_the_tags_still_merge_when_the_client_DOES_have_a_page(self):
        """The fallback must not quietly stop routing clicks for real consoles."""
        client = GuiClient(CID)
        client.page_stack.append(self.page)
        try:
            self.assertIsNotNone(gui_page_for_client(CID))
            panel = self._panel()
            panel.present_panel(FakeEvent(CID), panel.panels[0], _IconSize())
        finally:
            from sbs_utils.agent import Agent
            Agent.all.pop(CID, None)


class _IconSize:
    x = 2.0
    y = 2.0


if __name__ == "__main__":
    unittest.main()


class NoPathYetIsNotACrash(unittest.TestCase):
    """`$INFO_PATH` is absent until a panel is SHOWN and claims the shared name.

    Engine-measured on 1.3.11, from Storm's Beacon: a console reached that state and the
    info panel's TICK raised `'NoneType' object has no attribute 'upper'` EVERY FRAME,
    filling mast.runtime.log with one repeated traceback. Every reader of the variable did
    `path.upper()` on it unguarded; the writer already defaulted, which is why it was only
    ever seen from the tick.
    """

    def _task(self):
        """A GUI task whose variables are empty - exactly the pre-first-panel state."""
        class _T:
            def __init__(self):
                self.vars = {}
                self.main = None
            def get_variable(self, name, default=None):
                return self.vars.get(name, default)
            def set_variable(self, name, value):
                self.vars[name] = value
        return _T()

    def test_the_tick_returns_instead_of_raising(self):
        from sbs_utils.procedural.gui import tabbed_panel as TP

        class _Panel:
            client_id = 1
        task = self._task()
        real = TP.gui_task_for_client
        TP.gui_task_for_client = lambda cid: task
        try:
            self.assertEqual(0, TP.gui_panel_console_message_tick(_Panel()))
        finally:
            TP.gui_task_for_client = real

    def test_the_readers_return_instead_of_raising(self):
        from sbs_utils.procedural.gui import tabbed_panel as TP
        task = self._task()
        real = TP.gui_task_for_client
        TP.gui_task_for_client = lambda cid: task
        try:
            # None of these may raise with no path set.
            TP.gui_panel_console_message(1, 0, 0, 10, 10)
            TP.gui_panel_console_message_list(1, 0, 0, 10, 10)
        finally:
            TP.gui_task_for_client = real
