"""Slice 2 of MAST-authored web pages: Gui.web_page_open dispatch.

A //web/<path> route can be opened as a GUI session for a browser ("web")
client id. The session:
  * is discovered by path via the route label's .path
  * runs the route label as its GUI task (not the console/main label)
  * lives in Gui.clients so widget events route by client_id
  * is exempt from Gui.present's engine-console purge (web clients are not in
    sbs.get_client_ID_list())
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

WEB_CODE = """
//web/scores
    gui_text("SCORES PAGE")
    await gui()

//web/admin/panel
    gui_text("ADMIN PANEL")
    await gui()

//web/greet
    default name = "stranger"
    gui_text("hello")
    await gui()
"""

WEB_ID = 0x8080000000000042  # a web (non-engine) client id


class WebTestPage(StoryPage):
    story = None  # compiled per-test in setUp


class TestWebPageOpen(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(WEB_CODE, "webtest", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        WebTestPage.story = story
        FrameContext.mast = story          # _find_web_label fallback
        Gui._server_start_page = WebTestPage
        Gui._client_start_page = WebTestPage

    def tearDown(self):
        Gui.clients = {}
        Gui.web_client_ids = set()
        WebTestPage.story = None

    def test_open_unknown_path_returns_false(self):
        self.assertFalse(Gui.web_page_open(WEB_ID, "does_not_exist"))
        self.assertNotIn(WEB_ID, Gui.clients)

    def test_open_runs_the_web_route(self):
        self.assertTrue(Gui.web_page_open(WEB_ID, "scores"))
        self.assertIn(WEB_ID, Gui.clients)
        self.assertIn(WEB_ID, Gui.web_client_ids)
        page = Gui.clients[WEB_ID].page
        # GUI task started at the //web/scores route label, not main
        self.assertTrue(page.gui_task.active_label.startswith("__route__web/scores"))

    def test_path_accepts_web_prefix(self):
        self.assertTrue(Gui.web_page_open(WEB_ID, "web/scores"))
        self.assertIn(WEB_ID, Gui.clients)

    def test_nested_path(self):
        self.assertTrue(Gui.web_page_open(WEB_ID, "admin/panel"))
        page = Gui.clients[WEB_ID].page
        self.assertTrue(page.gui_task.active_label.startswith("__route__web/admin/panel"))

    def test_present_does_not_purge_web_client(self):
        Gui.web_page_open(WEB_ID, "scores")
        # The engine client list does NOT include the web id; a normal client
        # would be purged here. The web client must survive.
        self.assertNotIn(WEB_ID, sbs.get_client_ID_list())
        Gui.present(FakeEvent(0, "gui_present"))
        self.assertIn(WEB_ID, Gui.clients)

    def test_query_data_seeds_page_variables(self):
        # /web/greet?name=World -> the page's GUI task sees name="World"
        self.assertTrue(Gui.web_page_open(WEB_ID, "greet", data={"name": "World"}))
        task = Gui.clients[WEB_ID].page.gui_task
        self.assertEqual(task.get_variable("name"), "World")

    def test_no_query_keeps_default(self):
        # Without data, the route's `default name` applies.
        self.assertTrue(Gui.web_page_open(WEB_ID, "greet"))
        task = Gui.clients[WEB_ID].page.gui_task
        self.assertEqual(task.get_variable("name"), "stranger")

    def test_web_client_has_web_role(self):
        from sbs_utils.procedural.roles import role
        Gui.web_page_open(WEB_ID, "scores")
        self.assertIn(WEB_ID, role("__web__"))

    def test_navigate_switches_page_in_session(self):
        Gui.web_page_open(WEB_ID, "scores")
        gui_client = Gui.clients[WEB_ID]
        self.assertTrue(Gui.web_page_navigate(WEB_ID, "admin/panel"))
        # Same session (same GuiClient), now on the admin route
        self.assertIs(Gui.clients[WEB_ID], gui_client)
        self.assertTrue(
            gui_client.page.gui_task.active_label.startswith("__route__web/admin/panel"))

    def test_navigate_unknown_path_returns_false(self):
        Gui.web_page_open(WEB_ID, "scores")
        self.assertFalse(Gui.web_page_navigate(WEB_ID, "nope"))

    def test_navigate_non_web_client_returns_false(self):
        self.assertFalse(Gui.web_page_navigate(WEB_ID, "scores"))  # never opened

    def test_close_removes_web_client(self):
        Gui.web_page_open(WEB_ID, "scores")
        Gui.web_page_close(WEB_ID)
        self.assertNotIn(WEB_ID, Gui.clients)
        self.assertNotIn(WEB_ID, Gui.web_client_ids)


if __name__ == "__main__":
    unittest.main()
