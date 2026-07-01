"""Static rendering: frames_to_html embeds a one-shot snapshot into the mockgui
renderer (client.html) as window.__STATIC_FRAMES__, before the main script, so
the page renders once with no WebSocket.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.webproxy.static_render import frames_to_html

FRAMES = [
    {"clientID": 1, "cmd": "clear", "tag": ""},
    {"clientID": 1, "cmd": "text", "parent": "", "tag": "104",
     "style": "$text:`Hello`;", "left": 5, "top": 5, "right": 95, "bottom": 95},
    {"clientID": 1, "cmd": "complete", "tag": ""},
]


class TestFramesToHtml(unittest.TestCase):
    def test_embeds_frames_global(self):
        html = frames_to_html(FRAMES)
        self.assertIn("__STATIC_FRAMES__", html)
        self.assertIn("Hello", html)

    def test_global_defined_before_main_script(self):
        # The renderer reads window.__STATIC_FRAMES__ on load, so it must be set
        # before client.html's main script (which contains `function connect`).
        html = frames_to_html(FRAMES)
        i_frames = html.index("__STATIC_FRAMES__")
        i_connect = html.index("function connect")
        self.assertLess(i_frames, i_connect)

    def test_after_body_open(self):
        html = frames_to_html(FRAMES)
        i_body = html.lower().index("<body")
        i_frames = html.index("__STATIC_FRAMES__")
        self.assertLess(i_body, i_frames)

    def test_produces_full_document(self):
        html = frames_to_html(FRAMES)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("</html>", html)

    def test_empty_frames_ok(self):
        html = frames_to_html([])
        self.assertIn("window.__STATIC_FRAMES__ = [];", html)


if __name__ == "__main__":
    unittest.main()
