"""web_refresh / web_living: update a live //web page (e.g. a leaderboard) and
declare a page living/persistent from inside its route body.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural import web

WEB = 0x8080000000000042
WEB2 = 0x8080000000000043

# The scores page counts its renders (shared) and declares itself living.
CODE = """
//web/scores
    web_living(persist=True, refresh=5)
    shared SCORES_RENDERS = get_shared_variable("SCORES_RENDERS", 0) + 1
    set_shared_variable("SCORES_RENDERS", SCORES_RENDERS)
    gui_section("area: 5,5,95,95;")
    gui_text("BOARD")
    await gui()

//web/other
    gui_section("area: 5,5,95,95;")
    gui_text("OTHER")
    await gui()
"""


class _Page(StoryPage):
    story = None


class TestWebRefresh(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        Gui.web_render_sink = None
        web.web_living_clear()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        story = MastStory()
        self.assertEqual(story.compile(CODE, "wr", story), [])
        story.compiler_errors = []
        _Page.story = story
        Gui._server_start_page = _Page
        Gui._client_start_page = _Page

    def tearDown(self):
        Gui.clients = {}
        Gui.web_client_ids = set()
        _Page.story = None
        web.web_living_clear()

    def _renders(self):
        from sbs_utils.procedural.execution import get_shared_variable
        return get_shared_variable("SCORES_RENDERS", 0)

    def test_web_path_recorded(self):
        Gui.web_page_open(WEB, "scores")
        self.assertEqual(Gui.clients[WEB].page.web_path, "scores")

    def test_refresh_repaints_matching_sessions(self):
        Gui.web_page_open(WEB, "scores")
        Gui.web_page_open(WEB2, "scores")
        base = self._renders()
        n = web.web_refresh("scores")
        self.assertEqual(n, 2)                 # both scores sessions
        self.assertEqual(self._renders(), base + 2)

    def test_refresh_ignores_other_pages(self):
        Gui.web_page_open(WEB, "scores")
        Gui.web_page_open(WEB2, "other")
        base = self._renders()
        n = web.web_refresh("scores")
        self.assertEqual(n, 1)                 # only the scores session
        self.assertEqual(self._renders(), base + 1)

    def test_refresh_accepts_web_prefix(self):
        Gui.web_page_open(WEB, "scores")
        self.assertEqual(web.web_refresh("web/scores"), 1)

    def test_web_living_registers_from_body(self):
        Gui.web_page_open(WEB, "scores")       # route body calls web_living(...)
        pages = web.web_living_pages()
        self.assertIn("scores", pages)
        self.assertEqual(pages["scores"], {"persist": True, "refresh": 5})
        self.assertNotIn("other", pages)

    def test_refresh_no_sessions_is_zero(self):
        self.assertEqual(web.web_refresh("scores"), 0)


if __name__ == "__main__":
    unittest.main()
