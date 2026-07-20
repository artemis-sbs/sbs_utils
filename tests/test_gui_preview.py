"""Smoke test for the GUI Editor's live preview (cosmos_dev/gui_preview.py):
a design code block compiles and presents on a client, emitting its layout;
invalid code returns compile errors rather than raising. (End-to-end fidelity is
verified in a real running mock; this covers the compile + present path.)
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from cosmos_dev.gui_preview import present_gui_code

WEB_ID = 0x8080000000000042


class _CaptureSbs:
    def __init__(self, real):
        self._real = real
        self.cmds = []

    def __getattr__(self, name):
        if name.startswith("send_gui") or name == "send_client_widget_list":
            return lambda *a, **k: self.cmds.append((name, a))
        return getattr(self._real, name)


class TestGuiPreview(unittest.TestCase):
    def setUp(self):
        clear_shared()
        Gui.clients = {}
        Gui.web_client_ids = set()
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

    def test_presents_a_design(self):
        # Exactly what the GUI Editor generates: a labelled gui with layout, an
        # on gui_message handler, and a trailing await gui().
        code = ('=== my_gui\n'
                '    gui_section("area: 5,5,95,95;")\n'
                '    gui_text("$text:HELLO PREVIEW;")\n'
                '    with gui_grid(2):\n'
                '        gui_button("A")\n'
                '        gui_button("B")\n'
                '    on gui_message(gui_button("A")):\n'
                '        ~~ x = 1 ~~\n'
                '    await gui()')
        # A preview client that survives Gui.present's engine-console purge.
        Gui.web_client_ids.add(WEB_ID)
        real = FrameContext.context.sbs
        cap = _CaptureSbs(real)
        FrameContext.context.sbs = cap
        try:
            errors = present_gui_code(code, client_id=WEB_ID)
            self.assertEqual(errors, [])
            for _ in range(6):
                Gui.present(FakeEvent(0, "gui_present"))
        finally:
            FrameContext.context.sbs = real
        blob = " || ".join(str(a) for (m, a) in cap.cmds if m == "send_gui_text")
        self.assertIn("HELLO PREVIEW", blob, f"captured: {cap.cmds}")

    def test_presents_a_web_page(self):
        # A .web.mast page: a //web/<path> route. Its label name is generated, so
        # present_gui_code must resolve it and start there.
        code = ('//web/scores\n'
                '    gui_section("area: 5,5,95,95;")\n'
                '    gui_text("$text:WEB HELLO;")\n'
                '    await gui()')
        Gui.web_client_ids.add(WEB_ID)
        real = FrameContext.context.sbs
        cap = _CaptureSbs(real)
        FrameContext.context.sbs = cap
        try:
            errors = present_gui_code(code, client_id=WEB_ID)
            self.assertEqual(errors, [])
            for _ in range(6):
                Gui.present(FakeEvent(0, "gui_present"))
        finally:
            FrameContext.context.sbs = real
        blob = " || ".join(str(a) for (m, a) in cap.cmds if m == "send_gui_text")
        self.assertIn("WEB HELLO", blob, f"captured: {cap.cmds}")

    def test_invalid_code_returns_errors(self):
        errors = present_gui_code('with gui_grid(:\n    gui_text("x")', client_id=WEB_ID)
        self.assertTrue(errors, "expected compile errors for malformed code")


if __name__ == "__main__":
    unittest.main()
