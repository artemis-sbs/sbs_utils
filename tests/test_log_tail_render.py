"""The ambient log strip END TO END: does its text actually reach the engine?

Two bugs hid this strip on every console at once, and neither was visible to the store
tests in test_log_tail.py, which only check WHICH entries are picked:

  * with nothing logged, the strip rendered empty text -- and a text area sends each line
    as $text:`text`;style, so empty text arrives as $text:``; and draws a LONE BACKTICK.
  * gui_log_tail() runs once, while the console lays itself out, so later messages never
    appeared unless something pushed them in.

So these tests render a real MAST page through the web harness and read the emitted
send_gui_text stream, the same technique as test_gui_list. That is the level the bugs
lived at.
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
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.procedural import log_panel as LP
from sbs_utils.procedural.gui.log_panel_gui import log_tail_refresh

TAIL_CODE = """
//web/tail
    gui_section("area: 5,5,95,95;")
    gui_row("row-height: 4em;")
    gui_log_tail()
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


class TailPage(StoryPage):
    story = None


class TailRenderTests(unittest.TestCase):
    def setUp(self):
        LP.log_clear()
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(TAIL_CODE, "tailtest", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        TailPage.story = story
        FrameContext.mast = story
        Gui._server_start_page = TailPage
        Gui._client_start_page = TailPage

    def tearDown(self):
        Gui.clients = {}
        Gui.web_client_ids = set()
        TailPage.story = None
        LP.log_clear()

    def _render(self, after_open=None):
        shims = {}
        Gui.web_render_sink = lambda cid, real: shims.setdefault(cid, _CaptureSbs(real))
        try:
            Gui.web_page_open(WEB_ID, "tail")
            for i in range(6):
                if i == 3 and after_open is not None:
                    after_open()
                Gui.present(FakeEvent(0, "gui_present"))
                # The engine runs the dirty pass AFTER present each tick (handlerhooks),
                # and an in-place widget update is drawn by that pass, not by present.
                Dirty.represent_dirty()
        finally:
            Gui.web_render_sink = None
        cap = shims[WEB_ID]
        return " || ".join(str(a) for (m, a) in cap.cmds if m == "send_gui_text")

    def test_a_logged_message_is_drawn(self):
        LP.log_add(WEB_ID, "Docked at DS 1")
        self.assertIn("Docked at DS 1", self._render())

    def test_an_empty_strip_is_not_a_bare_backtick(self):
        blob = self._render()
        self.assertNotIn("$text:``", blob,
                         "empty text renders as a lone backtick on screen")
        self.assertIn(LP.LOG_TAIL_EMPTY, blob)

    def test_a_message_logged_AFTER_layout_reaches_the_widget(self):
        """The strip is built ONCE. Without the push it keeps its first frame forever.

        Asserted on the widget and the dirty queue rather than the emitted stream: the
        capture sink wraps Gui.present only, and an in-place update is drawn by the
        engine's dirty pass afterwards (handlerhooks), which writes to the real sbs.
        Reaching that queue IS the contract - the engine redraws whatever is in it.
        """
        from sbs_utils.procedural.gui.log_panel_gui import _TAILS
        self._render()                       # build the strip, log empty
        area = _TAILS[WEB_ID][0]
        self.assertEqual([LP.LOG_TAIL_EMPTY], area.value)

        Dirty.dirty = {}
        LP.log_add(WEB_ID, "Hull breach on deck 4")
        log_tail_refresh(WEB_ID)

        self.assertEqual(["Hull breach on deck 4"], area.value)
        queued = Dirty.dirty.get(area.client_id, set())
        self.assertIn(area, queued, "the engine only redraws what is queued dirty")

    def test_the_push_carries_the_STYLE_too(self):
        """line_styles is fixed at construction, so a value-only update would leave the
        previous entry's color on the new line - a warning could inherit chatter's."""
        from sbs_utils.procedural.gui.log_panel_gui import _TAILS
        LP.log_add(WEB_ID, "just chatter")
        self._render()
        area = _TAILS[WEB_ID][0]
        LP.log_add(WEB_ID, "reactor critical", severity="danger")
        log_tail_refresh(WEB_ID)
        self.assertEqual(["reactor critical"], area.value)
        blob = str(area.line_styles)
        self.assertIn(LP.LOG_CALLOUT_FONT, blob, f"styles did not follow the text: {blob}")
