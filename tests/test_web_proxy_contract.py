"""The host proxy drives the engine purely through self-contained dev-queue eval
expressions (cosmos_dev.webproxy.proxy._call). This locks that contract: eval'd
the way the dev-queue consumer would, those expressions must open a web page,
drain browser-shaped frames, route a widget event, and close the session.

This verifies everything about the real-engine web path except the live engine
process and the browser render (which the user verifies).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from cosmos_dev.webproxy.proxy import _call
from cosmos_dev.webproxy import engine_side
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent

CID = 0x8080000000000001

CODE = """
//web/scores
    default title = "SCORES"
    gui_section("area: 5,5,95,95;")
    spawn_btn = gui_button("Spawn")
    on gui_message(spawn_btn):
        npc_spawn(0, 0, 0, "S", "tsn, station", "starbase_command", "behav_station")
    gui_text("{title}")
    await gui()
"""


class _Page(StoryPage):
    story = None


class TestProxyContract(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        engine_side.uninstall()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        story = MastStory()
        self.assertEqual(story.compile(CODE, "px", story), [])
        story.compiler_errors = []
        _Page.story = story
        Gui._server_start_page = _Page
        Gui._client_start_page = _Page
        # Fresh globals, exactly like the dev-queue consumer (_exec_globals).
        self.g = {"__builtins__": __builtins__}

    def tearDown(self):
        engine_side.uninstall()
        Gui.clients = {}
        Gui.web_client_ids = set()
        _Page.story = None

    def _present(self, n=5):
        for _ in range(n):
            Gui.present(FakeEvent(0, "gui_present"))

    def test_full_proxy_expression_roundtrip(self):
        # open with a query param
        self.assertTrue(eval(_call("web_open", CID, "scores", {"title": "Hi"}), self.g))
        self._present()
        frames = eval(_call("web_drain"), self.g)
        cmds = {f["cmd"] for f in frames}
        self.assertIn("text", cmds)
        self.assertIn("button", cmds)
        self.assertTrue(all(f["clientID"] == CID for f in frames))
        # query param reached the page
        self.assertTrue(any("Hi" in f.get("style", "") for f in frames))

        # drain clears
        self.assertEqual(eval(_call("web_drain"), self.g), [])

        # a widget event routes back and mutates the world
        btn = next(f for f in frames if f["cmd"] == "button")
        before = len(sbs.sim.space_objects)
        eval(_call("web_event", CID,
                   {"tag": "gui_message", "sub_tag": btn["tag"]}), self.g)
        self._present()
        self.assertEqual(len(sbs.sim.space_objects), before + 1)

        # close removes the session
        eval(_call("web_close", CID), self.g)
        self.assertNotIn(CID, Gui.clients)


if __name__ == "__main__":
    unittest.main()
