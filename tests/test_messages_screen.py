"""Driving the real inbox screen: build it, click a row, rebuild, read the pane.

This file exists because the bug it pins was reported from the engine THREE times and
survived two fixes that were reasoned about rather than driven. Both earlier attempts
were sound in themselves and neither touched the actual cause.

The cause: `gui_console_enter` - the one door, and how the away console is entered -
writes CONSOLE_TYPE into the client's inventory and NEVER sets `page.console`, which is
only assigned at swap time from `gui_console()`. A morphed console therefore reported
no console at all, so `message_select` returned early and nothing a crew member picked
was ever stored.

A unit test on the model could not see it, because the model was right. Only building
the screen and pressing the widget shows it.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.gui import GuiClient
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.messages import (
    message_send, message_inbox, message_selected, message_revision, message_is_read)
from sbs_utils.procedural.gui import messages_gui

CID = 7


class _Main:
    def __init__(self, page):
        self.page = page


class _Task:
    """Enough of a GUI task for style parsing, props formatting and a dropdown."""

    def __init__(self):
        self.main = None

    def jump(self, label):
        pass

    def tick_in_context(self):
        pass

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s

    def eval_code_checked(self, code):
        return True

    def get_id(self):
        return 1


class _Sim:
    time_tick_counter = 0


class ScreenBase(unittest.TestCase):
    #: What `gui_console_enter` writes. A MORPHED console (the away one) reports an
    #: empty `page.console`, which is exactly the condition that broke this.
    console_type = "away"
    page_console = ""

    def setUp(self):
        FrameContext.context = Context(_Sim(), sbs, FakeEvent(CID, "test"))
        clear_shared()
        GuiClient(0)
        GuiClient(CID)
        page = StoryPage()
        page.pending_gui = False
        page.client_id = CID
        page.console = self.page_console
        page.gui_task = _Task()
        page.gui_task.main = _Main(page)
        self.page = page
        FrameContext.page = page
        FrameContext.task = page.gui_task
        set_inventory_value(CID, "CONSOLE_TYPE", self.console_type)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None

    def build(self):
        self.page.pending_layouts = []
        self.page.pending_row = None
        messages_gui.gui_messages_screen()

    def widgets(self):
        out = []

        def walk(o):
            out.append(o)
            for attr in ("rows", "columns"):
                for c in getattr(o, attr, None) or ():
                    walk(c)
        for layout in self.page.pending_layouts:
            walk(layout)
        if self.page.pending_row is not None:
            walk(self.page.pending_row)
        return out

    def listbox(self):
        return next((w for w in self.widgets() if isinstance(w, LayoutListbox)), None)

    def click(self, msg):
        """Press a row, the way the engine does: set the value, deliver the event."""
        lb = self.listbox()
        self.assertIsNotNone(lb, "the inbox drew no list to click")
        lb.value = msg
        lb.on_message(FakeEvent(CID, "gui_message", sub_tag=lb.tag))
        return lb


class TestSelectingAMessage(ScreenBase):
    def setUp(self):
        super().setUp()
        message_send("first", to="away", sender="A")
        message_send("second", to="away", sender="B")
        self.inbox = message_inbox()
        self.newest, self.oldest = self.inbox[0], self.inbox[1]

    def test_A_MORPHED_CONSOLE_CAN_SELECT_AT_ALL(self):
        """Reported three times as "selecting other messages does nothing".

        gui_console_enter never sets page.console, so the reader had no identity and
        message_select returned early. Every pick was dropped on the floor.
        """
        self.build()
        self.assertIsNone(message_selected())
        self.click(self.oldest)
        self.assertEqual(message_selected(), self.oldest["id"])

    def test_the_pane_shows_what_was_clicked_after_the_repaint(self):
        self.build()
        self.click(self.oldest)
        self.build()
        self.assertEqual(message_selected(), self.oldest["id"])

    def test_clicking_moves_the_revision_so_the_screen_repaints(self):
        """Without this the pick is stored and nothing redraws - which looks
        identical to the pick being dropped."""
        self.build()
        before = message_revision()
        self.click(self.oldest)
        self.assertNotEqual(message_revision(), before)

    def test_clicking_marks_it_read(self):
        self.build()
        self.click(self.oldest)
        self.assertTrue(message_is_read(self.oldest["id"]))

    def test_and_it_can_be_changed_again(self):
        self.build()
        self.click(self.oldest)
        self.build()
        self.click(self.newest)
        self.assertEqual(message_selected(), self.newest["id"])


class TestAnOrdinaryBridgeConsole(ScreenBase):
    """The path that always worked keeps working: page.console is set, and
    CONSOLE_TYPE agrees with it."""

    console_type = "engineering"
    page_console = "normal_engi"

    def test_selecting_works_there_too(self):
        message_send("one", sender="A")
        message_send("two", sender="B")
        oldest = message_inbox("engineering")[1]
        self.build()
        self.click(oldest)
        self.assertEqual(message_selected("engineering"), oldest["id"])


class TestAnEmptyInbox(ScreenBase):
    def test_it_draws_without_a_list_and_does_not_raise(self):
        self.build()
        self.assertIsNone(self.listbox())
        self.assertTrue(self.page.pending_layouts)


if __name__ == "__main__":
    unittest.main()
