"""WebRenderSink must serialise send_gui_* into exactly the wire commands the
cosmos_dev.mockgui browser (client.html) already understands, so the existing
renderer is reused unchanged for real-engine web pages.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.webproxy.render_sink import WebRenderSink, make_sink_factory

CID = 0x8080000000000042


class _RealSbs:
    """Stand-in 'real' sbs to prove non-gui calls forward through."""
    def get_ship_of_client(self, cid):
        return 999


class TestWebRenderSink(unittest.TestCase):
    def setUp(self):
        self.sink = WebRenderSink(CID, _RealSbs())

    def test_clear_and_complete(self):
        self.sink.send_gui_clear(CID, "")
        self.sink.send_gui_complete(CID, "")
        self.assertEqual(self.sink.drain(), [
            {"clientID": CID, "cmd": "clear", "tag": ""},
            {"clientID": CID, "cmd": "complete", "tag": ""},
        ])

    def test_text_widget_matches_mockgui_shape(self):
        self.sink.send_gui_text(CID, "", "104", "$text:`Hi`;", 5.0, 5.0, 95.0, 95.0)
        self.assertEqual(self.sink.drain(), [{
            "clientID": CID, "cmd": "text", "parent": "", "tag": "104",
            "style": "$text:`Hi`;",
            "left": 5.0, "top": 5.0, "right": 95.0, "bottom": 95.0,
        }])

    def test_button_widget(self):
        self.sink.send_gui_button(CID, "", "7", "sty", 1, 2, 3, 4)
        cmd = self.sink.drain()[0]
        self.assertEqual(cmd["cmd"], "button")
        self.assertEqual((cmd["left"], cmd["top"], cmd["right"], cmd["bottom"]), (1, 2, 3, 4))

    def test_face_and_slider_extra_params(self):
        self.sink.send_gui_face(CID, "", "f", "ter 1 2 3", 0, 0, 10, 10)
        self.sink.send_gui_slider(CID, "", "s", 0.5, "sty", 0, 0, 10, 10)
        face, slider = self.sink.drain()
        self.assertEqual(face["cmd"], "face")
        self.assertEqual(face["face_string"], "ter 1 2 3")
        self.assertEqual(slider["cmd"], "slider")
        self.assertEqual(slider["current"], 0.5)

    def test_widget_list_is_swallowed(self):
        # console view lists are irrelevant to web pages and must not leak
        self.sink.send_client_widget_list(CID, "", "3dview^2dview")
        self.assertEqual(self.sink.drain(), [])

    def test_non_gui_calls_forward_to_real(self):
        self.assertEqual(self.sink.get_ship_of_client(CID), 999)

    def test_out_callback_streams_instead_of_buffering(self):
        out = []
        sink = WebRenderSink(CID, _RealSbs(), out=out.append)
        sink.send_gui_clear(CID, "")
        self.assertEqual(sink.frames, [])           # nothing buffered
        self.assertEqual(out, [{"clientID": CID, "cmd": "clear", "tag": ""}])

    def test_factory_returns_persistent_sink_per_client(self):
        f = make_sink_factory()
        s1 = f(CID, _RealSbs())
        s2 = f(CID, _RealSbs())
        self.assertIs(s1, s2)                        # same client -> same sink
        self.assertIsNot(f(CID + 1, _RealSbs()), s1) # different client -> new sink


if __name__ == "__main__":
    unittest.main()
