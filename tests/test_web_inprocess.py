"""In-process web serving for non-engine MAST hosts: handle_web_client_event
dispatches browser web_connect/web_disconnect straight to Gui (no dev queue,
no render sink) and ignores non-web client events.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from cosmos_dev.webproxy import inprocess
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent

WEB = 0x8080000000000042
CODE = """
//web/scores
    gui_section("area: 5,5,95,95;")
    gui_text("SCORES")
    await gui()
"""


class _Page(StoryPage):
    story = None


class TestInProcess(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        Gui.web_render_sink = None
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        story = MastStory()
        self.assertEqual(story.compile(CODE, "ip", story), [])
        story.compiler_errors = []
        _Page.story = story
        Gui._server_start_page = _Page
        Gui._client_start_page = _Page

    def tearDown(self):
        Gui.clients = {}
        Gui.web_client_ids = set()
        _Page.story = None

    def test_web_connect_opens_page_no_sink(self):
        handled = inprocess.handle_web_client_event(
            {"event": "web_connect", "clientID": WEB, "path": "scores"})
        self.assertTrue(handled)
        self.assertIn(WEB, Gui.clients)
        self.assertIn(WEB, Gui.web_client_ids)
        # in-process needs no render sink (renders through the live sbs)
        self.assertIsNone(Gui.web_render_sink)

    def test_web_disconnect_closes(self):
        inprocess.handle_web_client_event(
            {"event": "web_connect", "clientID": WEB, "path": "scores"})
        handled = inprocess.handle_web_client_event(
            {"event": "web_disconnect", "clientID": WEB})
        self.assertTrue(handled)
        self.assertNotIn(WEB, Gui.clients)

    def test_console_connect_not_handled(self):
        handled = inprocess.handle_web_client_event(
            {"event": "connect", "clientID": WEB})
        self.assertFalse(handled)
        self.assertNotIn(WEB, Gui.clients)

    def test_query_passed_through(self):
        inprocess.handle_web_client_event(
            {"event": "web_connect", "clientID": WEB, "path": "scores",
             "query": {"title": "Hi"}})
        task = Gui.clients[WEB].page.gui_task
        self.assertEqual(task.get_variable("title"), "Hi")


if __name__ == "__main__":
    unittest.main()
