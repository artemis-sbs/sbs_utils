"""In-engine web-proxy API (cosmos_dev.webproxy.engine_side): open/drain/event/
close a //web page and get browser-ready wire frames, driven the way the host
proxy drives it over the dev queue. Runs under the mock; no live engine needed.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from cosmos_dev.webproxy import engine_side
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
    spawn_btn = gui_button("Spawn")
    on gui_message(spawn_btn):
        npc_spawn(0, 0, 0, "S", "tsn, station", "starbase_command", "behav_station")
    gui_text("SCORES")
    await gui()
"""


class _Page(StoryPage):
    story = None


class TestEngineSide(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        engine_side.uninstall()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        story = MastStory()
        self.assertEqual(story.compile(CODE, "es", story), [])
        story.compiler_errors = []
        _Page.story = story
        Gui._server_start_page = _Page
        Gui._client_start_page = _Page

    def tearDown(self):
        engine_side.uninstall()
        Gui.clients = {}
        Gui.web_client_ids = set()
        _Page.story = None

    def _present(self, n=5):
        for _ in range(n):
            Gui.present(FakeEvent(0, "gui_present"))

    def test_open_then_drain_yields_wire_frames(self):
        self.assertTrue(engine_side.web_open(WEB, "scores"))
        self._present()
        frames = engine_side.web_drain()
        cmds = {f["cmd"] for f in frames}
        self.assertIn("text", cmds)
        self.assertIn("button", cmds)
        # All frames addressed to the web client
        self.assertTrue(all(f["clientID"] == WEB for f in frames))

    def test_drain_clears(self):
        engine_side.web_open(WEB, "scores")
        self._present()
        self.assertTrue(engine_side.web_drain())
        self.assertEqual(engine_side.web_drain(), [])   # nothing new

    def test_open_unknown_route_returns_false(self):
        self.assertFalse(engine_side.web_open(WEB, "nope"))

    def test_event_routes_to_page(self):
        engine_side.web_open(WEB, "scores")
        self._present()
        frames = engine_side.web_drain()
        # The Spawn button's tag comes straight off its rendered wire frame.
        btn = next(f for f in frames if f["cmd"] == "button")
        before = len(sbs.sim.space_objects)
        engine_side.web_event(WEB, {"tag": "gui_message", "sub_tag": btn["tag"]})
        self._present()
        self.assertEqual(len(sbs.sim.space_objects), before + 1)

    def test_close_removes_session(self):
        engine_side.web_open(WEB, "scores")
        engine_side.web_close(WEB)
        self.assertNotIn(WEB, Gui.clients)

    def test_push_mode_streams_ndjson_to_file(self):
        import json
        import os
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "web_frames.ndjson")
        engine_side.set_frames_file(path)     # PUSH mode
        engine_side.web_open(WEB, "scores")
        self._present()
        with open(path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        cmds = {c["cmd"] for c in lines}
        self.assertIn("text", cmds)
        self.assertIn("button", cmds)
        self.assertTrue(all(c["clientID"] == WEB for c in lines))
        # push mode does not buffer for pull
        self.assertEqual(engine_side.web_drain(), [])

    def test_snapshot_renders_and_leaves_no_session(self):
        frames = engine_side.web_snapshot("scores", ticks=6)
        cmds = {f["cmd"] for f in frames}
        self.assertIn("text", cmds)
        self.assertIn("button", cmds)
        # one-shot: no lingering session, and the live sink is restored (None)
        self.assertNotIn(engine_side._SNAPSHOT_CID, Gui.clients)
        self.assertIsNone(Gui.web_render_sink)

    def test_snapshot_missing_route_returns_none(self):
        self.assertIsNone(engine_side.web_snapshot("nope"))

    def test_snapshot_preserves_live_push_sink(self):
        import os
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "web_frames.ndjson")
        engine_side.set_frames_file(path)             # live push mode active
        live_sink = Gui.web_render_sink
        engine_side.web_snapshot("scores", ticks=3)   # must not disturb it
        self.assertIs(Gui.web_render_sink, live_sink)
        self.assertEqual(engine_side._frames_path, path)

    def test_persist_writes_frames_file(self):
        import json
        import os
        import tempfile
        d = tempfile.mkdtemp()
        out = engine_side.web_persist("scores", ticks=6, out_dir=d)
        self.assertIsNotNone(out)
        self.assertTrue(os.path.isfile(out))
        with open(out) as f:
            frames = json.load(f)
        cmds = {c["cmd"] for c in frames}
        self.assertIn("text", cmds)
        self.assertIn("button", cmds)
        # no lingering session from the persist snapshot
        self.assertNotIn(engine_side._SNAPSHOT_CID, Gui.clients)

    def test_persist_missing_route_returns_none(self):
        import tempfile
        self.assertIsNone(engine_side.web_persist("nope", out_dir=tempfile.mkdtemp()))

    def test_set_frames_file_truncates(self):
        import os
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "web_frames.ndjson")
        with open(path, "w") as f:
            f.write('{"stale": true}\n')
        engine_side.set_frames_file(path)     # must truncate
        self.assertEqual(os.path.getsize(path), 0)


if __name__ == "__main__":
    unittest.main()
