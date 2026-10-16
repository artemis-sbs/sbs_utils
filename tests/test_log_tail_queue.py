"""The one-line console strip QUEUES lines instead of replacing them at once.

Seen in the engine (author course 3, lesson 5): Dr Hale reads the name tags, Six Names
completes, and its `Then: signal names_known` completes Account for the Crew in the same
call. Two `Quest complete:` lines arrived together; the strip shows ONE line, so the first
was replaced in under half a second and no player ever saw it.

Now a line the strip has put up stays LOG_TAIL_HOLD sim seconds before the next replaces
it, a timer brings the next one in, and a lone line after a quiet spell is not delayed.

Driven through a real MAST page (`gui_log_tail` in a web page) and the real push
(`log_notify`, the front door `comms_broadcast` uses), with the TickDispatcher ticked the
way the engine ticks it.

    python -m unittest tests.test_log_tail_queue
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  registers route/gui nodes
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import log_panel as LP
from sbs_utils.procedural.gui import log_panel_gui as LPG

QUEUE_CODE = """
//web/qtail
    gui_section("area: 5,5,95,95;")
    gui_row("row-height: 4em;")
    gui_log_tail()
    await gui()
"""

QID = 0x8080000000000043


class QueuePage(StoryPage):
    story = None


class LogTailQueueTests(unittest.TestCase):
    def setUp(self):
        LP.log_clear()
        TickDispatcher.clear()
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        story = MastStory()
        errors = story.compile(QUEUE_CODE, "tailqueue", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        QueuePage.story = story
        FrameContext.mast = story
        Gui._server_start_page = QueuePage
        Gui._client_start_page = QueuePage

    def tearDown(self):
        Gui.clients = {}
        Gui.web_client_ids = set()
        QueuePage.story = None
        TickDispatcher.clear()
        LP.log_clear()

    def build(self):
        Gui.web_page_open(QID, "qtail")
        for _ in range(4):
            Gui.present(FakeEvent(0, "gui_present"))
            Dirty.represent_dirty()
        self.assertIn(QID, LPG._TAILS, "the strip never registered")
        return LPG._TAILS[QID][0]

    def wait(self, seconds):
        """Let sim time pass a tick at a time, dispatching ticks as the engine does."""
        for _ in range(int(seconds * TickDispatcher.tps)):
            sbs.sim._time_tick_counter += 1
            FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "mission_tick"))
            TickDispatcher.dispatch_tick()

    def say(self, text):
        LPG.log_notify(QID, text, category="mission")

    def test_two_lines_together_each_get_their_turn(self):
        area = self.build()
        self.say("Quest complete: Six Names")
        self.say("Quest complete: Account for the Crew")
        self.assertEqual(["Quest complete: Six Names"], area.value,
                         "the first line was replaced at once")
        self.wait(LP.LOG_TAIL_HOLD - 0.5)
        self.assertEqual(["Quest complete: Six Names"], area.value, "held too briefly")
        self.wait(1.0)
        self.assertEqual(["Quest complete: Account for the Crew"], area.value,
                         "the queued line never came in")

    def test_a_lone_line_is_not_delayed(self):
        area = self.build()
        self.say("Docked at DS 1")
        self.assertEqual(["Docked at DS 1"], area.value)
        self.wait(LP.LOG_TAIL_HOLD + 1)
        self.say("Undocked")
        self.assertEqual(["Undocked"], area.value, "a line after a quiet spell waited")

    def test_three_in_a_row_drain_in_order(self):
        area = self.build()
        for n in ("one", "two", "three"):
            self.say(n)
        seen = [area.value[0]]
        for _ in range(3):
            self.wait(LP.LOG_TAIL_HOLD + 0.2)
            if area.value[0] != seen[-1]:
                seen.append(area.value[0])
        self.assertEqual(["one", "two", "three"], seen)

    def test_a_rebuild_mid_burst_keeps_the_queue(self):
        """The console laying itself out again must not jump past a line still due."""
        area = self.build()
        self.say("first")
        self.say("second")
        LPG._TAILS.clear()
        area = self.build()
        self.assertEqual(["first"], area.value, "the rebuild skipped the queue")
        self.wait(LP.LOG_TAIL_HOLD + 0.5)
        self.assertEqual(["second"], area.value)

    def test_a_console_opening_later_does_not_replay_history(self):
        self.say("old one")
        self.say("old two")
        self.wait(LP.LOG_TAIL_HOLD + 1)
        area = self.build()
        self.assertEqual(["old two"], area.value)


if __name__ == "__main__":
    unittest.main()
