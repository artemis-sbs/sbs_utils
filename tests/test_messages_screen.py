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
    message_send, message_inbox, message_selected, message_revision, message_is_read,
    message_select)
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


class TestAFrameThatCannotSeeTheConsole(ScreenBase):
    """A moment when the console does not resolve is not the same fact as "no mail".

    It used to be treated as one, and it cost two repaints and an empty screen between
    them: `message_inbox()` filtered to nothing, and `message_revision()` dropped its
    per-console part - so the number the screen repaints ON moved, the empty build was
    drawn, the next frame resolved the console again, the number moved back, and it
    repainted a second time. Reported as "change the dropdown and it repaints empty"
    and "sometimes it looks like two list boxes" (2026-09-02).

    Both halves are pinned here, because either one alone still produces a symptom: a
    stable revision with an empty inbox blanks the panel silently, and a full inbox
    with a moving revision repaints for no reason.
    """

    console_type = "away"

    def setUp(self):
        super().setUp()
        message_send("one", to="away", sender="A")
        message_send("two", to="away", sender="B")
        self.build()
        self.inbox = len(message_inbox())
        self.revision = message_revision()
        self.assertEqual(self.inbox, 2)

    def test_no_page_at_all_answers_the_same(self):
        """`on change` expressions are evaluated on the task, and the frame's page is
        not guaranteed to be set when they run."""
        saved = FrameContext.page
        FrameContext.page = None
        try:
            self.assertEqual(len(message_inbox()), self.inbox)
            self.assertEqual(message_revision(), self.revision)
        finally:
            FrameContext.page = saved

    def test_a_console_that_reports_nothing_answers_the_same(self):
        """A morphed console mid-swap: CONSOLE_TYPE not written yet and `page.console`
        still empty - the exact hole `_here` was built for."""
        set_inventory_value(CID, "CONSOLE_TYPE", "")
        self.page.console = ""
        self.assertEqual(len(message_inbox()), self.inbox)
        self.assertEqual(message_revision(), self.revision)

    def test_BUT_A_REAL_CONSOLE_CHANGE_STILL_WINS(self):
        """Sticky must not mean stuck. Moving to a console with no away mail shows an
        empty inbox, because that one really is empty."""
        set_inventory_value(CID, "CONSOLE_TYPE", "science")
        self.assertEqual(len(message_inbox()), 0)
        self.assertNotEqual(message_revision(), self.revision)


class TestItUpdatesInsteadOfRebuilding(ScreenBase):
    """The screen is built ONCE, and a change touches only what changed.

    It used to repaint the whole page on every `message_revision()` move - the route
    ran `jump epadd_messages_screen`, which tears down and redraws the chrome, the list,
    the reading pane and the compose line because one number changed. That is what made
    the panel flicker, what let it be caught mid-build showing an empty list, and what
    made scrolling look like two overlapping list boxes (2026-09-02).

    A listbox re-renders its own rows from `items`; the reading pane is a sub-section
    that can be refilled alone. Neither needs the page.
    """

    console_type = "away"

    def setUp(self):
        super().setUp()
        message_send("one", to="away", sender="A", subject="First")
        message_send("two", to="away", sender="B", subject="Second")
        self.build()
        self.view = getattr(self.page, messages_gui.VIEW_ATTR)
        self.layouts = len(self.page.pending_layouts)

    def pane_text(self):
        out, seen = [], set()

        def walk(o, d=0):
            if d > 8 or id(o) in seen:
                return
            seen.add(id(o))
            m = getattr(o, "message", None)
            if isinstance(m, str):
                out.append(m)
            for attr in ("rows", "columns"):
                for c in getattr(o, attr, None) or ():
                    walk(c, d + 1)
        walk(self.view["pane"].sub_section)
        return " ".join(out)

    def test_NEW_MAIL_TOUCHES_THE_LIST_AND_NOTHING_ELSE(self):
        message_send("three", to="away", sender="C", subject="Third")
        self.assertTrue(messages_gui.gui_messages_tick())
        self.assertEqual(len(self.view["lb"].items), 3)
        self.assertEqual(len(self.page.pending_layouts), self.layouts,
                         "a new layout means the page was rebuilt")

    def test_SELECTING_A_MESSAGE_ACTUALLY_SENDS_IT(self):
        """The bug this class did not catch the first time.

        `rebuild()` empties the pane's rows and the refill builds new widgets, but
        neither marks anything dirty - so the pane changed in the MODEL and nothing ever
        reached the client. Reported from the engine as "selecting a message doesn't show
        the message", and every test here passed throughout, because they all read the
        model.

        So this one counts what is put on the wire. Measured before the fix: zero.
        """
        for layout in self.page.pending_layouts:
            layout.calc(CID)
            layout.present(FakeEvent(CID))
        oldest = message_inbox()[-1]
        message_select(oldest.get("id"))

        sent = []
        real = sbs.send_gui_text
        sbs.send_gui_text = (lambda cid, parent, tag, props, l, t, r, b:
                             sent.append(props))
        try:
            messages_gui.gui_messages_tick()
        finally:
            sbs.send_gui_text = real
        self.assertTrue(sent, "the pane was refilled but never transmitted")
        self.assertTrue(any("First" in s for s in sent),
                        "the selected message was not among what was sent: %r" % (sent,))

    def test_a_new_selection_refills_only_the_pane(self):
        oldest = message_inbox()[-1]
        message_select(oldest.get("id"))
        messages_gui.gui_messages_tick()
        self.assertIn("First", self.pane_text())
        self.assertEqual(len(self.page.pending_layouts), self.layouts)

    def test_the_unread_count_updates_in_place(self):
        """The chrome carries it, and the widget exists even at zero - so the count can
        come and go without a rebuild to bring the line into being."""
        sub = self.view["subtitle"]
        self.assertIsNotNone(sub)
        message_send("four", to="away", sender="D", subject="Fourth")
        messages_gui.gui_messages_tick()
        self.assertIn("unread", sub.message or "")

    def test_a_tick_with_no_screen_up_does_nothing(self):
        """The handler can outlive the screen; it must not raise or half-draw."""
        delattr(self.page, messages_gui.VIEW_ATTR)
        self.assertFalse(messages_gui.gui_messages_tick())

    def test_THE_ROUTE_CALLS_THE_TICK_AND_DOES_NOT_JUMP(self):
        """The library half is useless if the mission still jumps its own label."""
        import os
        mast = os.path.join(os.path.dirname(__file__), "..", "..",
                            "LegendaryMissions", "consoles", "epadd.mast")
        if not os.path.exists(mast):
            self.skipTest("LegendaryMissions is not checked out beside sbs_utils")
        with open(mast, encoding="utf-8") as f:
            src = f.read()
        # The ROUTE still jumps - that is how the screen is entered. What must not
        # happen is the WATCHER jumping, which is the full repaint.
        watcher = src.split("on change message_revision():")[-1]
        self.assertIn("gui_messages_tick()", watcher.split("await gui()")[0])
        self.assertNotIn("jump epadd_messages_screen",
                         watcher.split("await gui()")[0],
                         "the inbox watcher is still repainting the whole page")


class TestTheReadingPaneLeavesNothingBehind(ScreenBase):
    """The reported bug, from a real bridge: the inbox "creating numerous text areas
    instead of updating the one that is there" - three messages' titles, senders and
    bodies drawn on top of each other, unreadable.

    A refill allocates NEW tags, and the engine keeps drawing a tag until something
    takes it away. `rebuild()` empties the model and says nothing to the client, so
    every earlier fill stayed painted underneath. What is checked here is that every
    widget the previous fill drew is re-sent OFF SCREEN before the new one is drawn.
    """

    def setUp(self):
        super().setUp()
        message_send("Body one, the good pan.", to="away", sender="Devi",
                     subject="Did you take the good pan")
        message_send("Body two, entirely different.", to="away", sender="Zed",
                     subject="Second")
        self.inbox = message_inbox()
        self.build()
        self.pane = getattr(self.page, messages_gui.VIEW_ATTR)["pane"]
        self.pane.sub_section.calc(CID)
        self.pane.sub_section.present(FakeEvent(CID, "gui_present"))

    def pane_tags(self):
        """The tags of the widgets that actually DRAW - the leaves.

        A Row and a Layout carry tags too but send nothing unless they have a
        background, so asking for those to be retired would measure the harness."""
        out = []

        def walk(o):
            kids = getattr(o, "rows", None) or getattr(o, "columns", None)
            if kids:
                for c in kids:
                    walk(c)
                return
            tag = getattr(o, "tag", None)
            if tag is not None:
                out.append(str(tag))
        walk(self.pane.sub_section)
        return out

    def sends(self):
        """(tag, left, top) for everything drawn while the recorder is installed."""
        calls = []
        originals = {}
        for name in ("send_gui_text", "send_gui_button", "send_gui_image"):
            originals[name] = getattr(sbs, name)

            def rec(cid, parent, tag, props, left, top, right, bottom,
                    _o=originals[name], _c=calls):
                _c.append((str(tag), left, top))
                return _o(cid, parent, tag, props, left, top, right, bottom)
            setattr(sbs, name, rec)
        self.addCleanup(lambda: [setattr(sbs, n, o) for n, o in originals.items()])
        return calls

    def test_EVERY_WIDGET_THE_OLD_FILL_DREW_LEAVES_THE_SCREEN(self):
        before = set(self.pane_tags())
        self.assertTrue(before, "the pane drew nothing to begin with")

        calls = self.sends()
        message_select(self.inbox[1]["id"])
        messages_gui.gui_messages_tick()

        after = set(self.pane_tags())
        self.assertTrue(after.isdisjoint(before),
                        "the refill reused tags - this test no longer measures anything")
        # Off screen is Bounds.hidden, a long way negative. Every old tag has to have
        # been sent there; a tag that was never mentioned again is still painted.
        for tag in before:
            sent = [c for c in calls if c[0] == tag]
            self.assertTrue(sent, f"widget {tag} was dropped without being retired - "
                                  "the engine is still drawing it")
            self.assertLess(sent[-1][1], -100, f"widget {tag} is still on screen")
            self.assertLess(sent[-1][2], -100, f"widget {tag} is still on screen")

    def test_and_the_new_message_is_drawn_where_it_should_be(self):
        """The retirement must not take the REPLACEMENT off screen with it."""
        calls = self.sends()
        message_select(self.inbox[1]["id"])
        messages_gui.gui_messages_tick()

        new = set(self.pane_tags())
        drawn = [c for c in calls if c[0] in new]
        self.assertTrue(drawn, "the pane refilled but nothing was sent")
        self.assertTrue(all(c[1] > -100 and c[2] > -100 for c in drawn),
                        "the new fill landed off screen")

    def test_A_GHOST_BUTTON_IS_THE_DANGEROUS_ONE(self):
        """A stale line of text is unreadable; a stale reply BUTTON is still there to
        be pressed, wired to the message that is no longer on screen."""
        asked = message_send("Do we hold?", to="away", sender="The Captain",
                             choices=["Hold", "Fall back"])
        message_select(asked["id"])
        messages_gui.gui_messages_tick()
        buttons = [t for t in self.pane_tags()]
        self.assertTrue(buttons)

        calls = self.sends()
        message_select(self.inbox[1]["id"])
        messages_gui.gui_messages_tick()
        for tag in buttons:
            sent = [c for c in calls if c[0] == tag]
            self.assertTrue(sent, f"reply widget {tag} was left on screen")
            self.assertLess(sent[-1][1], -100, f"reply widget {tag} is still pressable")

    def test_a_pane_that_never_presented_retires_nothing(self):
        """Nothing was drawn, so there is nothing to take back - and no client to
        send it to. This is the freshly-built page, before its first present."""
        self.build()
        pane = getattr(self.page, messages_gui.VIEW_ATTR)["pane"]
        pane.sub_section.client_id = None
        self.assertFalse(pane.clear())


class TestAnEmptyInbox(ScreenBase):
    def test_it_draws_without_a_list_and_does_not_raise(self):
        self.build()
        self.assertIsNone(self.listbox())
        self.assertTrue(self.page.pending_layouts)


if __name__ == "__main__":
    unittest.main()
