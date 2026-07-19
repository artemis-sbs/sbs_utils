"""gui_list spike: prove the `with gui_list(items) as item:` row-template
mechanism end to end. The `with` body must run once PER item (not once), with
the `as` name bound to each row, building one row of output per item.

We run a real MAST gui page through the web harness and capture the emitted
send_gui_text commands (same technique as test_web_page's render-sink test).
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

LIST_CODE = """
//web/ships
    gui_section("area: 5,5,95,95;")
    ships = ["Alpha", "Beta", "Gamma"]
    with gui_list(ships) as ship:
        gui_text("ROW {ship}")
    await gui()

//web/cells
    gui_section("area: 5,5,95,95;")
    ships = [{"name":"Alpha","hull":90}, {"name":"Beta","hull":40}]
    with gui_list(ships) as ship:
        gui_text("N:{ship['name']}")
        gui_text("H:{ship['hull']}")
    gui_text("FOOTER")
    await gui()

//web/empty
    gui_section("area: 5,5,95,95;")
    nothing = []
    with gui_list(nothing) as x:
        gui_text("SHOULD_NOT_APPEAR {x}")
    gui_text("ONLY_FOOTER")
    await gui()
"""

WEB_ID = 0x8080000000000042


class _CaptureSbs:
    def __init__(self, real):
        self._real = real
        self.cmds = []

    def __getattr__(self, name):
        if name.startswith("send_gui") or name == "send_client_widget_list":
            return lambda *a, **k: self.cmds.append((name, a))
        return getattr(self._real, name)


class WebListPage(StoryPage):
    story = None


class TestGuiList(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(LIST_CODE, "listtest", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        WebListPage.story = story
        FrameContext.mast = story
        Gui._server_start_page = WebListPage
        Gui._client_start_page = WebListPage

    def tearDown(self):
        Gui.clients = {}
        Gui.web_client_ids = set()
        WebListPage.story = None

    def _render(self, path):
        shims = {}
        Gui.web_render_sink = lambda cid, real: shims.setdefault(cid, _CaptureSbs(real))
        try:
            Gui.web_page_open(WEB_ID, path)
            for _ in range(6):
                Gui.present(FakeEvent(0, "gui_present"))
        finally:
            Gui.web_render_sink = None
        cap = shims[WEB_ID]
        texts = [str(a) for (m, a) in cap.cmds if m == "send_gui_text"]
        return cap, texts, " || ".join(texts)

    def test_row_template_runs_once_per_item(self):
        cap, texts, blob = self._render("ships")
        self.assertIn("ROW Alpha", blob, f"captured: {cap.cmds}")
        self.assertIn("ROW Beta", blob, f"captured: {cap.cmds}")
        self.assertIn("ROW Gamma", blob, f"captured: {cap.cmds}")

    def test_multiple_widgets_are_row_cells_and_footer_runs_once(self):
        cap, texts, blob = self._render("cells")
        # each item contributed both cells, bound from the dict item
        self.assertIn("N:Alpha", blob)
        self.assertIn("H:90", blob)
        self.assertIn("N:Beta", blob)
        self.assertIn("H:40", blob)
        # content after the `with` runs exactly once (loop exited past the block)
        self.assertEqual(sum("FOOTER" in t for t in texts), 1, f"captured: {cap.cmds}")

    def test_empty_list_renders_no_rows(self):
        cap, texts, blob = self._render("empty")
        self.assertNotIn("SHOULD_NOT_APPEAR", blob)
        self.assertIn("ONLY_FOOTER", blob)


if __name__ == "__main__":
    unittest.main()
