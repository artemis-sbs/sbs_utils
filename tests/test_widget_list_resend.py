"""send_client_widget_list goes out when the list CHANGES, not on every repaint.

That call is how the engine learns which native widgets a console has, and
acting on it means building them (2d view, waterfall, ship_data...). swap_layout
sets gui_state='repaint' on every GUI rebuild, so re-sending unconditionally
asked the engine to redo that work every time a console's MAST screen rebuilt --
while a screen with no engine widgets (the empty list) cost nothing. That
asymmetry is exactly what "consoles are slow to come up, plain tabs are instant"
looks like from the outside.

Skipping the repeat is only safe because send_gui_clear does NOT drop the
engine's widgets -- the "refresh" present branch clears and re-presents without
ever re-sending the list, and consoles keep their widgets across a resize.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # registers route/gui nodes
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent

CODE = """
jump helm_screen

== helm_screen ==
    gui_console("helm")
    gui_section("area: 5,5,95,95;")
    gui_text("HELM")
    await gui()

== helm_again ==
    gui_console("helm")
    gui_section("area: 5,5,95,95;")
    gui_text("HELM REBUILT")
    await gui()

== science_screen ==
    gui_console("science")
    gui_section("area: 5,5,95,95;")
    gui_text("SCIENCE")
    await gui()

== plain_screen ==
    gui_section("area: 5,5,95,95;")
    gui_text("NO ENGINE WIDGETS")
    await gui()
"""

CID = 1


class WidgetListPage(StoryPage):
    story = None


class _Base(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(CODE, "widgetlisttest", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        WidgetListPage.story = story
        FrameContext.mast = story

        self.sends = []
        self._orig = sbs.send_client_widget_list

        def tap(client_id, console, widgets, *a, **k):
            self.sends.append((client_id, console, widgets))
            return self._orig(client_id, console, widgets, *a, **k)

        sbs.send_client_widget_list = tap

        self.page = WidgetListPage()
        Gui.push(CID, self.page)

    def tearDown(self):
        sbs.send_client_widget_list = self._orig
        Gui.clients = {}
        Gui.widget_list_sent = {}
        WidgetListPage.story = None

    def repaint(self):
        """Force one full repaint of the page, the way a rebuild does."""
        self.page.gui_state = "repaint"
        self.page.present(FakeEvent(CID, "gui_present"))

    def goto(self, label):
        self.page.gui_task.jump(label)
        self.page.gui_task.tick_in_context()
        self.page.present(FakeEvent(CID, "gui_present"))


class TestWidgetListResend(_Base):
    def test_first_paint_sends_the_list(self):
        self.assertTrue(self.sends, "a console's first paint must establish its widgets")
        self.assertEqual(self.sends[-1][1], "normal_helm")

    def test_repeat_repaint_does_not_resend(self):
        before = len(self.sends)
        self.repaint()
        self.repaint()
        self.repaint()
        self.assertEqual(len(self.sends), before,
                         "an unchanged widget list must not be re-sent")

    def test_rebuilding_the_same_console_does_not_resend(self):
        # A different label, same gui_console -> same widget list. This is the
        # common case: a console screen rebuilding itself.
        before = len(self.sends)
        self.goto("helm_again")
        self.assertEqual(len(self.sends), before)

    def test_changing_console_does_resend(self):
        before = len(self.sends)
        self.goto("science_screen")
        self.assertEqual(len(self.sends), before + 1)
        self.assertEqual(self.sends[-1][1], "normal_sci")

    def test_leaving_for_a_widgetless_screen_resends_the_empty_list(self):
        # The engine must be told to drop the console's widgets.
        self.goto("plain_screen")
        self.assertEqual(self.sends[-1][1], "")
        self.assertEqual(self.sends[-1][2], "")

    def test_returning_to_a_console_resends(self):
        self.goto("plain_screen")
        before = len(self.sends)
        self.goto("helm_screen")
        self.assertEqual(len(self.sends), before + 1)
        self.assertEqual(self.sends[-1][1], "normal_helm")

    def test_a_new_page_reestablishes_the_list(self):
        # A pushed page must not inherit the page-underneath's "already sent"
        # belief, even when it happens to want the same widgets.
        before = len(self.sends)
        Gui.push(CID, WidgetListPage())
        self.assertEqual(len(self.sends), before + 1)

    def test_pop_reestablishes_the_list(self):
        # The page revealed by a pop re-sends on its next repaint: the page that
        # left may have replaced the list.
        Gui.push(CID, WidgetListPage())
        Gui.clients[CID].pop()
        before = len(self.sends)
        self.repaint()
        self.assertEqual(len(self.sends), before + 1)


if __name__ == "__main__":
    unittest.main()
